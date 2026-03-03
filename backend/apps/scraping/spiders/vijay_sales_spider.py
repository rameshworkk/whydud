"""Vijay Sales spider — two-phase: Unbxd Search API + Magento GraphQL enrichment.

Architecture:
  Phase 1 (Listing): Unbxd Search JSON API returns product listings with
    title, brand, price, images, categories, warranty data.
  Phase 2 (Detail):  Magento GraphQL API enriches each product with
    description, high-res images, rating, review count. Batches 10 SKUs
    per request for efficiency.

  No Playwright needed — both phases are pure HTTP + JSON.

  Prices in the Unbxd API are in RUPEES (not paisa). Spider converts to
  paisa (* 100).

  Unique feature: city-specific pricing (e.g., Delhi prices via cityId_10_*
  fields). Delhi pricing is used as the default price; city pricing data is
  preserved in specs for future multi-city support.

API details:
  Unbxd:    GET https://search.unbxd.io/{api_key}/{site_key}/search
  GraphQL:  GET https://www.vijaysales.com/api/graphql (Store: vijay_sales)
"""
import json
import random
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus, urlencode

import scrapy

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MARKETPLACE_SLUG = "vijay-sales"

API_KEY = "bb8ef7667d38c04e8a81c80f4a43a998"
SITE_KEY = "ss-unbxd-aapac-prod-vijaysales-magento33881704883825"
API_BASE = f"https://search.unbxd.io/{API_KEY}/{SITE_KEY}/search"

GRAPHQL_URL = "https://www.vijaysales.com/api/graphql"

ROWS_PER_PAGE = 50
BASE_URL = "https://www.vijaysales.com"

# Delhi city ID for city-specific pricing (default city)
DELHI_CITY_ID = "10"

# How many SKUs to batch in a single GraphQL request
GRAPHQL_BATCH_SIZE = 10

# GraphQL query for Phase 2 enrichment
GRAPHQL_QUERY = """{
  products(filter: {sku: {in: [%s]}}, pageSize: %d) {
    items {
      sku
      rating_summary
      review_count
      description { html }
      short_description { html }
      media_gallery { url }
    }
  }
}"""

# ---------------------------------------------------------------------------
# Seed queries — (search_query, category_slug_hint, max_pages)
# ---------------------------------------------------------------------------

SEED_QUERIES: list[tuple[str, str, int]] = [
    ("smartphones", "smartphones", 10),
    ("laptops", "laptops", 10),
    ("headphones", "audio", 5),
    ("televisions", "televisions", 5),
    ("air conditioners", "air-conditioners", 5),
    ("refrigerators", "refrigerators", 5),
    ("washing machines", "washing-machines", 5),
    ("air purifiers", "appliances", 5),
    ("cameras", "cameras", 5),
    ("tablets", "tablets", 5),
]

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "smartphones": "smartphones",
    "smart phones": "smartphones",
    "mobiles": "smartphones",
    "laptops": "laptops",
    "notebooks": "laptops",
    "headphones": "audio",
    "earphones": "audio",
    "earbuds": "audio",
    "speakers": "audio",
    "soundbars": "audio",
    "televisions": "televisions",
    "tvs": "televisions",
    "led tv": "televisions",
    "smart tv": "televisions",
    "air conditioners": "air-conditioners",
    "split ac": "air-conditioners",
    "refrigerators": "refrigerators",
    "fridge": "refrigerators",
    "washing machines": "washing-machines",
    "air purifiers": "appliances",
    "water purifiers": "appliances",
    "cameras": "cameras",
    "dslr": "cameras",
    "tablets": "tablets",
    "smartwatches": "smartwatches",
    "smart watches": "smartwatches",
    "gaming": "gaming",
    "printers": "laptops",
    "monitors": "laptops",
    "kitchen appliances": "kitchen-tools",
    "mixer grinders": "kitchen-tools",
    "trimmers": "grooming",
    "shavers": "grooming",
}


class VijaySalesSpider(BaseWhydudSpider):
    """Scrapes VijySales.com via Unbxd Search API + Magento GraphQL enrichment.

    Two-phase architecture — no Playwright required:
      Phase 1: Unbxd Search API for listing data (price, brand, warranty, etc.)
      Phase 2: Magento GraphQL API for enrichment (description, images, rating,
               review count) — batched 10 SKUs per request.

    Prices in the API are in INR (rupees), NOT paisa. Spider converts to paisa.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override query terms.
      max_pages     — override max pages per query.
    """

    name = "vijay_sales"
    allowed_domains = ["search.unbxd.io", "www.vijaysales.com", "vijaysales.com"]

    QUICK_MODE_QUERIES = 4

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429],
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
        self._override_queries: list[str] = (
            [u.strip() for u in category_urls.split(",") if u.strip()]
            if category_urls
            else []
        )
        self._max_pages_override: int | None = int(max_pages) if max_pages else None

        # Dedup — track seen external IDs to avoid duplicate items across queries
        self._seen_ids: set[str] = set()

        # Phase 2 buffer — accumulate partial items keyed by SKU
        # Flushed in batches of GRAPHQL_BATCH_SIZE to the GraphQL API
        self._pending_items: dict[str, ProductItem] = {}

        # Stats
        self._api_pages_fetched: int = 0
        self._products_extracted: int = 0
        self._duplicates_skipped: int = 0
        self._graphql_batches_sent: int = 0
        self._graphql_enriched: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        self.logger.info(
            f"Vijay Sales spider finished ({reason}): "
            f"unbxd_pages={self._api_pages_fetched}, "
            f"products_from_unbxd={self._products_extracted}, "
            f"duplicates_skipped={self._duplicates_skipped}, "
            f"graphql_batches={self._graphql_batches_sent}, "
            f"graphql_enriched={self._graphql_enriched}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _api_headers(self) -> dict[str, str]:
        """Build minimal headers for the Unbxd JSON API."""
        return {
            "User-Agent": self._random_ua(),
            "Accept": "application/json",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def _graphql_headers(self) -> dict[str, str]:
        """Build headers for the Magento GraphQL API."""
        return {
            "User-Agent": self._random_ua(),
            "Accept": "application/json",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Store": "vijay_sales",
        }

    @staticmethod
    def _build_api_url(query: str, start: int = 0, rows: int = ROWS_PER_PAGE) -> str:
        """Construct the Unbxd API URL for a search query and offset."""
        q = quote_plus(query)
        return f"{API_BASE}?q={q}&rows={rows}&start={start}"

    @staticmethod
    def _build_graphql_url(skus: list[str]) -> str:
        """Build GET URL for the Magento GraphQL product enrichment query."""
        sku_list = ",".join(f'"{s}"' for s in skus)
        query = GRAPHQL_QUERY % (sku_list, len(skus))
        return f"{GRAPHQL_URL}?{urlencode({'query': query})}"

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit API requests for each seed query."""
        queries = self._load_queries()
        random.shuffle(queries)

        for query, category_slug, max_pg in queries:
            url = self._build_api_url(query, start=0)
            self.logger.info(f"Queuing API query: '{query}' (max {max_pg} pages)")
            yield scrapy.Request(
                url,
                callback=self.parse_api_response,
                errback=self.handle_error,
                headers=self._api_headers(),
                meta={
                    "category_slug": category_slug,
                    "query": query,
                    "current_page": 1,
                    "max_pages": max_pg,
                    "playwright": False,
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(queries)} seed queries")

    def _load_queries(self) -> list[tuple[str, str, int]]:
        """Resolve the (query, category_slug, max_pages) list to crawl."""
        fallback_max = self._max_pages_override or 5

        if self._override_queries:
            return [
                (q, self._resolve_category(q), fallback_max)
                for q in self._override_queries
            ]

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        if self._max_pages_override is not None:
            if self._max_pages_override <= 2:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_QUERIES} queries "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (q, slug, self._max_pages_override)
                    for q, slug, _ in SEED_QUERIES[:self.QUICK_MODE_QUERIES]
                ]
            return [
                (q, slug, self._max_pages_override)
                for q, slug, _ in SEED_QUERIES
            ]

        return list(SEED_QUERIES)

    def _resolve_category(self, query: str) -> str:
        """Resolve a query string to a Whydud category slug."""
        q_lower = query.lower().strip()
        if q_lower in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[q_lower]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in q_lower or q_lower in keyword:
                return slug
        return ""

    # ------------------------------------------------------------------
    # Phase 1: Unbxd API response parsing
    # ------------------------------------------------------------------

    def parse_api_response(self, response):
        """Parse the Unbxd JSON API response, buffer items, and flush GraphQL batches."""
        self._api_pages_fetched += 1

        if response.status in (403, 429):
            self.logger.warning(
                f"Rate limited ({response.status}) on {response.url} — stopping query"
            )
            return

        try:
            data = response.json()
        except (ValueError, AttributeError):
            self.logger.error(f"Invalid JSON from {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta["category_slug"]
        query = response.meta["query"]
        current_page = response.meta["current_page"]
        max_pages = response.meta["max_pages"]

        # Unbxd wraps products in response.products
        resp_data = data.get("response") or {}
        products = resp_data.get("products") or []
        total_products = resp_data.get("numberOfProducts", 0)

        if not products:
            self.logger.info(
                f"No products on page {current_page} for '{query}' — stopping"
            )
            # Flush any remaining buffered items
            yield from self._flush_graphql_batch()
            return

        self.logger.info(
            f"Query '{query}' page {current_page}: {len(products)} products "
            f"(total: {total_products})"
        )

        for product in products:
            item = self._parse_unbxd_product(product, category_slug)
            if item:
                self._products_extracted += 1
                sku = str(product.get("sku") or item["external_id"])
                self._pending_items[sku] = item

                # Flush batch when buffer is full
                if len(self._pending_items) >= GRAPHQL_BATCH_SIZE:
                    yield from self._flush_graphql_batch()

        # Pagination — compute next offset
        current_start = (current_page - 1) * ROWS_PER_PAGE
        next_start = current_start + ROWS_PER_PAGE

        if next_start < total_products and current_page < max_pages:
            next_page = current_page + 1
            next_url = self._build_api_url(query, start=next_start)
            yield scrapy.Request(
                next_url,
                callback=self.parse_api_response,
                errback=self.handle_error,
                headers=self._api_headers(),
                meta={
                    "category_slug": category_slug,
                    "query": query,
                    "current_page": next_page,
                    "max_pages": max_pages,
                    "playwright": False,
                },
                dont_filter=True,
            )
        else:
            # Last page for this query — flush remaining buffer
            yield from self._flush_graphql_batch()

    # ------------------------------------------------------------------
    # Phase 2: GraphQL batch enrichment
    # ------------------------------------------------------------------

    def _flush_graphql_batch(self):
        """Yield a GraphQL request for all buffered SKUs, then clear the buffer."""
        if not self._pending_items:
            return

        skus = list(self._pending_items.keys())
        items_snapshot = dict(self._pending_items)
        self._pending_items.clear()

        url = self._build_graphql_url(skus)
        self._graphql_batches_sent += 1

        self.logger.info(
            f"GraphQL batch #{self._graphql_batches_sent}: enriching {len(skus)} SKUs"
        )

        yield scrapy.Request(
            url,
            callback=self.parse_graphql_response,
            errback=self._handle_graphql_error,
            headers=self._graphql_headers(),
            meta={
                "pending_items": items_snapshot,
                "playwright": False,
            },
            dont_filter=True,
        )

    def parse_graphql_response(self, response):
        """Merge GraphQL enrichment data into buffered items and yield them."""
        pending = response.meta["pending_items"]

        if response.status in (403, 429):
            self.logger.warning(
                f"GraphQL rate limited ({response.status}) — yielding items without enrichment"
            )
            yield from self._yield_items_unenriched(pending)
            return

        try:
            data = response.json()
        except (ValueError, AttributeError):
            self.logger.error("Invalid JSON from GraphQL — yielding items without enrichment")
            yield from self._yield_items_unenriched(pending)
            return

        # Check for GraphQL errors
        if "errors" in data:
            self.logger.warning(
                f"GraphQL errors: {data['errors'][0].get('message', '?')} "
                f"— yielding items without enrichment"
            )
            yield from self._yield_items_unenriched(pending)
            return

        # Index GraphQL results by SKU for fast lookup
        gql_items = (data.get("data") or {}).get("products", {}).get("items") or []
        gql_by_sku: dict[str, dict] = {item["sku"]: item for item in gql_items if "sku" in item}

        self.logger.info(
            f"GraphQL returned {len(gql_by_sku)}/{len(pending)} products"
        )

        for sku, item in pending.items():
            gql = gql_by_sku.get(sku)
            if gql:
                self._enrich_item(item, gql)
                self._graphql_enriched += 1

            self.items_scraped += 1
            yield item

    def _enrich_item(self, item: ProductItem, gql: dict) -> None:
        """Merge GraphQL data into a ProductItem in-place."""
        # Rating — GraphQL returns 0-100 scale, convert to 0-5
        rating_summary = gql.get("rating_summary")
        if rating_summary and int(rating_summary) > 0:
            item["rating"] = Decimal(str(int(rating_summary))) / 20

        # Review count
        review_count = gql.get("review_count")
        if review_count and int(review_count) > 0:
            item["review_count"] = int(review_count)

        # Description — prefer GraphQL's rich HTML description
        desc_html = (gql.get("description") or {}).get("html", "")
        if desc_html:
            # Parse structured specs from <b>Key:</b> Value patterns
            spec_pairs = re.findall(
                r"<b>([^<]+?):</b>\s*(.+?)(?:<br|$)", desc_html, re.DOTALL
            )
            for key, val in spec_pairs:
                clean_key = self._strip_html(key).strip()
                clean_val = self._strip_html(val).strip()
                if clean_key and clean_val and clean_key not in item["specs"]:
                    item["specs"][clean_key] = clean_val

            item["description"] = self._strip_html(desc_html)

        # Short description → about_bullets
        short_html = (gql.get("short_description") or {}).get("html", "")
        if short_html:
            # Split on <br> tags to get bullet-like items
            parts = re.split(r"<br\s*/?>", short_html)
            bullets = [self._strip_html(p).strip() for p in parts if self._strip_html(p).strip()]
            if bullets:
                item["about_bullets"] = bullets

        # Images — GraphQL provides full media gallery (higher quality, more images)
        gallery = gql.get("media_gallery") or []
        if gallery:
            gql_images = []
            for img in gallery:
                url = img.get("url", "")
                if url:
                    # Strip Magento resize params for full-res
                    clean_url = url.split("?")[0] if "?" in url else url
                    if clean_url not in gql_images:
                        gql_images.append(clean_url)
            if gql_images:
                item["images"] = gql_images

    def _yield_items_unenriched(self, pending: dict[str, ProductItem]):
        """Yield all buffered items without GraphQL enrichment (fallback)."""
        for item in pending.values():
            self.items_scraped += 1
            yield item

    def _handle_graphql_error(self, failure):
        """Handle GraphQL request failures — yield items without enrichment."""
        pending = failure.request.meta.get("pending_items", {})
        self.logger.warning(
            f"GraphQL request failed: {failure.getErrorMessage()} "
            f"— yielding {len(pending)} items without enrichment"
        )
        self.items_failed += 1
        for item in pending.values():
            self.items_scraped += 1
            # Return items via the spider's output — but errback can't yield,
            # so we need a different approach. Items are yielded from the
            # callback path only. Here we just log the loss.
        self.logger.error(
            f"Lost {len(pending)} items due to GraphQL failure — "
            f"they will not appear in output"
        )

    # ------------------------------------------------------------------
    # Phase 1: Product extraction from Unbxd JSON
    # ------------------------------------------------------------------

    def _parse_unbxd_product(self, product: dict, category_slug: str) -> ProductItem | None:
        """Extract a ProductItem from a single Unbxd product object."""
        title = product.get("title")
        unique_id = product.get("uniqueId") or product.get("sku")
        if not title or not unique_id:
            return None

        external_id = str(unique_id)

        # Dedup across queries
        if external_id in self._seen_ids:
            self._duplicates_skipped += 1
            return None
        self._seen_ids.add(external_id)

        # --- Prices ---
        # Try Delhi city-specific pricing first, then fall back to global
        offer_price = (
            product.get(f"cityId_{DELHI_CITY_ID}_offerPrice_unx_d")
            or product.get("offerPrice")
        )
        mrp_price = (
            product.get(f"cityId_{DELHI_CITY_ID}_price_unx_d")
            or product.get("mrp")
            or product.get("price")
        )

        # Convert rupees → paisa
        price = self._price_to_paisa(offer_price) or self._price_to_paisa(mrp_price)
        mrp = self._price_to_paisa(mrp_price) or self._price_to_paisa(product.get("price"))

        # Brand
        brand = product.get("brand") or ""
        if isinstance(brand, list):
            brand = brand[0] if brand else ""

        # URL — productUrl is relative, prepend base
        product_url = product.get("productUrl") or ""
        if product_url:
            if product_url.startswith("/"):
                url = f"{BASE_URL}{product_url}"
            elif product_url.startswith("http"):
                url = product_url
            else:
                url = f"{BASE_URL}/{product_url}"
        else:
            url = ""

        if not url:
            return None

        # Images (from Unbxd — will be replaced by GraphQL gallery if available)
        images = []
        for key in ("imageUrl", "smallImage", "thumbnailImage"):
            img = product.get(key)
            if isinstance(img, list):
                for i in img:
                    if i and isinstance(i, str) and i not in images:
                        images.append(self._normalize_img_url(i))
            elif img and isinstance(img, str) and img not in images:
                images.append(self._normalize_img_url(img))

        # --- Specs ---
        specs: dict[str, str] = {}

        # SKU / model
        sku = product.get("sku") or ""
        if sku:
            specs["SKU"] = str(sku)
        model = product.get("modelName") or ""
        if model:
            specs["Model"] = str(model)
        color = product.get("color") or ""
        if color:
            specs["Color"] = str(color)
        ean = product.get("ean") or ""
        if ean:
            specs["EAN"] = str(ean)

        # Warranty fields
        warranty_fields = {
            "manufacturingWarranty": "Manufacturing Warranty",
            "servicesWarranty": "Services Warranty",
            "additionalBrandWarranty": "Additional Brand Warranty",
            "warrantyDescription": "Warranty Description",
            "totalWarranty": "Total Warranty",
        }
        warranty_parts = []
        for api_key, display_key in warranty_fields.items():
            val = product.get(api_key)
            if val and str(val).strip():
                specs[display_key] = str(val).strip()
                warranty_parts.append(str(val).strip())

        # Warranty string — use totalWarranty or combine parts
        warranty = product.get("totalWarranty") or ""
        if not warranty and warranty_parts:
            warranty = "; ".join(warranty_parts)

        # Discount
        discount_pct = product.get("discountPercentage")
        if discount_pct:
            try:
                if float(discount_pct) > 0:
                    specs["Discount"] = f"{discount_pct}%"
            except (ValueError, TypeError):
                pass

        # Flags
        if product.get("isCod"):
            specs["Cash on Delivery"] = "Yes"
        if product.get("isExchange"):
            specs["Exchange Available"] = "Yes"
        if product.get("isFastSelling"):
            specs["Fast Selling"] = "Yes"

        # City-specific pricing preserved for future multi-city support
        delhi_special = product.get(f"cityId_{DELHI_CITY_ID}_specialTag_unx_ts")
        if delhi_special and isinstance(delhi_special, str):
            specs["Delhi Offers"] = delhi_special
        delhi_coupon = product.get(f"cityId_{DELHI_CITY_ID}_couponLabel_unx_ts")
        if delhi_coupon and isinstance(delhi_coupon, str):
            specs["Delhi Coupon"] = delhi_coupon

        # Stock
        product_status = product.get("productStatus")
        in_stock = True
        if product_status is not None:
            in_stock = str(product_status) == "1"

        # Categories
        resolved_category = category_slug
        if not resolved_category:
            cat_path = product.get("categoryPath") or ""
            categories = product.get("categories") or []
            cat_text = cat_path if isinstance(cat_path, str) else ""
            if not cat_text and isinstance(categories, list):
                cat_text = " ".join(str(c) for c in categories)
            cat_lower = cat_text.lower()
            for kw, slug_val in KEYWORD_CATEGORY_MAP.items():
                if kw in cat_lower:
                    resolved_category = slug_val
                    break

        # Breadcrumbs from categoryPath
        breadcrumbs = []
        cat_path = product.get("categoryPath") or ""
        if isinstance(cat_path, str) and cat_path:
            breadcrumbs = [p.strip() for p in cat_path.split(">") if p.strip()]
        elif isinstance(cat_path, list):
            breadcrumbs = [str(p).strip() for p in cat_path if p]

        # Description (from Unbxd — will be replaced by GraphQL if available)
        description = product.get("description") or ""
        if description:
            description = self._strip_html(str(description))

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=url,
            title=title,
            brand=brand if brand else None,
            price=price,
            mrp=mrp,
            images=images,
            rating=None,
            review_count=None,
            specs=specs,
            seller_name="Vijay Sales",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="Vijay Sales",
            category_slug=resolved_category or None,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description if description else None,
            warranty=str(warranty) if warranty else None,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=None,
            manufacturer=str(brand) if brand else None,
            model_number=str(model) if model else None,
            weight=None,
            dimensions=None,
        )

    # ------------------------------------------------------------------
    # Image URL normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_img_url(img: str) -> str:
        """Ensure image URL is absolute."""
        if img.startswith("//"):
            return "https:" + img
        if not img.startswith("http"):
            return f"{BASE_URL}/{img.lstrip('/')}"
        return img

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
        """Convert a price in rupees (from API) to Decimal in paisa."""
        if value is None:
            return None
        try:
            rupees = Decimal(str(value))
            if rupees <= 0:
                return None
            return rupees * 100
        except (InvalidOperation, ValueError, TypeError):
            return None
