"""Giva spider — scrapes products via Shopify's built-in JSON API.

Architecture:
  Single-phase: /products.json returns full product data (title, brand, prices,
  images, variants, tags, description) in one paginated response.
  No Playwright needed — pure HTTP + JSON.

  Collection endpoints (/collections/{slug}.json) are broken on Giva,
  so we use the global /products.json endpoint which returns all ~5,000 products
  across ~20 pages (250 per page).

  Prices in the Shopify API are in RUPEES (not paisa). Spider converts to paisa (* 100).

API details:
  Endpoint: GET https://www.giva.co/products.json?page={n}&limit=250
  Auth:     None required (public Shopify storefront API)
  Rate:     ~2 requests/second for Shopify storefront
  Total:    ~5,000 products across ~20 pages
"""

import random
import re
from decimal import Decimal, InvalidOperation

import scrapy

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MARKETPLACE_SLUG = "giva"

PRODUCTS_API = "https://www.giva.co/products.json"
PAGE_SIZE = 250  # Shopify max


class GivaSpider(BaseWhydudSpider):
    """Scrapes Giva.co via Shopify's public /products.json API.

    No Playwright required — pure HTTP requests returning JSON.

    Prices in the API are in INR (rupees), NOT paisa. Spider converts to paisa.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — ignored (Giva uses global product listing, not collections).
      max_pages     — override max pages to crawl (default 25).
    """

    name = "giva"
    allowed_domains = ["giva.co", "www.giva.co"]

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 0.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429],
        # No Playwright needed
        "PLAYWRIGHT_LAUNCH_OPTIONS": None,
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        job_id: str | None = None,
        category_urls: str | None = None,
        max_pages: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self._max_pages: int = int(max_pages) if max_pages else 25

        # Stats
        self._pages_fetched: int = 0
        self._products_extracted: int = 0
        self._seen_ids: set[str] = set()  # dedup by product ID

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        self.logger.info(
            f"Giva spider finished ({reason}): "
            f"pages={self._pages_fetched}, "
            f"products_extracted={self._products_extracted}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _api_headers(self) -> dict[str, str]:
        """Build minimal headers for the Shopify JSON API."""
        return {
            "User-Agent": self._random_ua(),
            "Accept": "application/json",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }

    @staticmethod
    def _build_api_url(page: int) -> str:
        """Construct the products API URL for a given page."""
        return f"{PRODUCTS_API}?page={page}&limit={PAGE_SIZE}"

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit the first page request."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        url = self._build_api_url(1)
        self.logger.info(
            f"Starting Giva scrape: /products.json (max {self._max_pages} pages, "
            f"{PAGE_SIZE} per page)"
        )
        yield scrapy.Request(
            url,
            callback=self.parse_products_page,
            errback=self.handle_error,
            headers=self._api_headers(),
            meta={
                "current_page": 1,
                "playwright": False,
            },
            dont_filter=True,
        )

    # ------------------------------------------------------------------
    # Products page parsing
    # ------------------------------------------------------------------

    def parse_products_page(self, response):
        """Parse a page of /products.json and yield ProductItems directly."""
        self._pages_fetched += 1
        current_page = response.meta["current_page"]

        if response.status == 429:
            self.logger.warning(
                f"Rate limited (429) on page {current_page} — stopping"
            )
            return

        if response.status == 403:
            self.logger.warning(
                f"Blocked (403) on page {current_page} — stopping"
            )
            return

        try:
            data = response.json()
        except (ValueError, AttributeError):
            self.logger.error(f"Invalid JSON from {response.url}")
            self.items_failed += 1
            return

        products = data.get("products") or []

        if not products:
            self.logger.info(
                f"No products on page {current_page} — reached end of catalog"
            )
            return

        self.logger.info(
            f"Page {current_page}: {len(products)} products"
        )

        # Extract products directly from the listing — it has full data
        for product_json in products:
            product_id = str(product_json.get("id", ""))
            if not product_id or product_id in self._seen_ids:
                continue
            self._seen_ids.add(product_id)

            item = self._extract_product(product_json)
            if item:
                self._products_extracted += 1
                self.items_scraped += 1
                yield item
            else:
                self.items_failed += 1

        # Pagination — if we got a full page, there might be more
        if len(products) >= PAGE_SIZE and current_page < self._max_pages:
            next_page = current_page + 1
            next_url = self._build_api_url(next_page)
            yield scrapy.Request(
                next_url,
                callback=self.parse_products_page,
                errback=self.handle_error,
                headers=self._api_headers(),
                meta={
                    "current_page": next_page,
                    "playwright": False,
                },
                dont_filter=True,
            )

    # ------------------------------------------------------------------
    # Product extraction
    # ------------------------------------------------------------------

    def _extract_product(self, product_json: dict) -> ProductItem | None:
        """Extract a ProductItem from a Shopify product JSON object."""
        title = (product_json.get("title") or "").strip()
        handle = product_json.get("handle", "")
        product_id = product_json.get("id")

        if not title or not handle or not product_id:
            return None

        external_id = str(product_id)
        url = f"https://www.giva.co/products/{handle}"

        # Brand — Shopify vendor field
        brand = product_json.get("vendor", "GIVA") or "GIVA"

        # Description — body_html contains HTML, strip to plain text
        body_html = product_json.get("body_html", "") or ""
        description = self._strip_html(body_html) if body_html else None

        # Variants — extract price from first available variant
        variants = product_json.get("variants") or []
        price = None
        mrp = None
        in_stock = False

        if variants:
            first_variant = variants[0]
            price = self._price_to_paisa(first_variant.get("price"))
            compare_price = first_variant.get("compare_at_price")
            mrp = self._price_to_paisa(compare_price) if compare_price else price

            # Check stock across all variants
            in_stock = any(v.get("available", False) for v in variants)

        # Images
        images = []
        for img in product_json.get("images") or []:
            src = img.get("src", "")
            if src:
                images.append(src)

        # Tags — can be a list or a comma-separated string depending on endpoint
        raw_tags = product_json.get("tags") or []
        if isinstance(raw_tags, str):
            tags = [t.strip() for t in raw_tags.split(",") if t.strip()]
        else:
            tags = raw_tags

        # Options — size, material, stone, etc.
        options = product_json.get("options") or []

        # Build specs from tags + options + product_type
        specs = self._build_specs(product_json, tags, options, variants)

        # Variant options in structured format (skip default "Title" option)
        variant_options = []
        for opt in options:
            opt_name = opt.get("name", "")
            opt_values = opt.get("values") or []
            if (
                opt_name
                and opt_values
                and opt_name != "Title"
                and opt_values != ["Default Title"]
            ):
                variant_options.append({
                    "name": opt_name,
                    "values": opt_values,
                })

        # Weight — prefer tag-extracted weight, fall back to variant grams
        weight = specs.get("Weight")
        if not weight and variants:
            w = variants[0].get("grams") or variants[0].get("weight")
            if w and float(w) > 0:
                weight = f"{w}g"
        if weight and not weight.endswith("g"):
            weight = f"{weight}g"

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=url,
            title=title,
            brand=brand if brand else None,
            price=price,
            mrp=mrp,
            images=images,
            rating=None,           # Shopify JSON API doesn't include reviews
            review_count=0,
            specs=specs,
            seller_name="GIVA",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="GIVA",
            category_slug="jewellery",
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=specs.get("Warranty"),
            delivery_info=None,
            return_policy=None,
            breadcrumbs=[],
            variant_options=variant_options,
            country_of_origin=specs.get("Country of Origin"),
            manufacturer=brand,
            model_number=specs.get("SKU"),
            weight=weight,
            dimensions=None,
        )

    # ------------------------------------------------------------------
    # Specs extraction
    # ------------------------------------------------------------------

    # Giva tags use "Key_Value" format. Map tag prefixes to spec labels.
    _TAG_SPEC_MAP: dict[str, str] = {
        "Metal": "Material",
        "Color": "Color",
        "plating": "Plating",
        "Stone": "Stone",
        "stoneColor": "Stone Color",
        "stoneSetting": "Stone Setting",
        "stoneShape": "Stone Shape",
        "lockType": "Lock Type",
        "thickness": "Thickness",
        "totalLength": "Length",
        "weight": "Weight",
        "Category": "Category",
        "subCategory": "Sub Category",
        "Style": "Style",
        "charmSize": "Charm Size",
        "extenderLength": "Extender Length",
    }

    def _build_specs(
        self,
        product_json: dict,
        tags: list[str],
        options: list[dict],
        variants: list[dict],
    ) -> dict[str, str]:
        """Build a specs dict from Shopify tags, options, and product metadata.

        Giva tags follow a structured "Key_Value" convention:
          Metal_925 Silver, Color_Rose Gold, plating_Rose Gold Micron, etc.
        """
        specs: dict[str, str] = {}

        # Product type
        product_type = product_json.get("product_type", "")
        if product_type:
            specs["Product Type"] = product_type

        # Parse structured Key_Value tags
        for tag in tags:
            tag = tag.strip()
            if "_" not in tag:
                # Non-structured tags — check for hallmark, plating info
                tag_lower = tag.lower()
                if "hallmark" in tag_lower and "Hallmark" not in specs:
                    specs["Hallmark"] = "Yes"
                continue

            prefix, _, value = tag.partition("_")
            value = value.strip()
            if not value or value.lower() in ("none", "0", ""):
                continue

            spec_label = self._TAG_SPEC_MAP.get(prefix)
            if spec_label and spec_label not in specs:
                specs[spec_label] = value

        # Hallmark from 925Hallmark_Yes tag
        for tag in tags:
            if tag.startswith("925Hallmark_"):
                val = tag.partition("_")[2].strip()
                if val.lower() == "yes":
                    specs["Hallmark"] = "BIS 925 Hallmarked"

        # Options -> specs (Size, etc.) — only add non-default options
        for opt in options:
            opt_name = opt.get("name", "").strip()
            opt_values = opt.get("values") or []
            if (
                opt_name
                and opt_values
                and opt_name != "Title"
                and opt_values != ["Default Title"]
            ):
                specs[opt_name] = ", ".join(str(v) for v in opt_values)

        # SKU from first variant
        if variants:
            sku = variants[0].get("sku", "")
            if sku:
                specs["SKU"] = sku

        return specs

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    _HTML_TAG_RE = re.compile(r"<[^>]+>")
    _MULTI_SPACE_RE = re.compile(r"\s+")

    @classmethod
    def _strip_html(cls, text: str) -> str:
        """Remove HTML tags and collapse whitespace."""
        clean = cls._HTML_TAG_RE.sub(" ", text)
        return cls._MULTI_SPACE_RE.sub(" ", clean).strip()

    # ------------------------------------------------------------------
    # Price helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _price_to_paisa(value) -> Decimal | None:
        """Convert a price in rupees (from Shopify API) to Decimal in paisa."""
        if value is None:
            return None
        try:
            rupees = Decimal(str(value))
            if rupees <= 0:
                return None
            return rupees * 100
        except (InvalidOperation, ValueError, TypeError):
            return None
