"""Reliance Digital spider — scrapes product listings and detail pages.

Architecture:
  Reliance Digital is a Vue.js 2 SPA powered by Fynd/Jio Commerce Platform.
  - Listing pages: window.__INITIAL_STATE__.productListingPage.productlists.items[]
  - Detail pages:  window.__INITIAL_STATE__.productDetailsPage.product
  - JSON-LD Product schema on detail pages as fallback
  - Prices in the JSON are in rupees (NOT paisa) — spider converts to paisa

URL patterns:
  Collection: /collection/{slug}?page_no={n}&page_size=12
  L2 Category: /products/?l2_category={slug}&department=electronics
  L3 Category: /products/?l3_categories={slug}&department=electronics
  Product:     /product/{product-slug}-{uid}
  Search:      /search?q={query}
"""
import json
import random
import re
from decimal import Decimal, InvalidOperation

import scrapy
from scrapy_playwright.page import PageMethod

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCT_UID_RE = re.compile(r"-(\d{5,})$")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "reliance-digital"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Smartphones
    "smart-phones": "smartphones",
    "smart phones": "smartphones",
    "smartphones": "smartphones",
    "feature-phones": "smartphones",
    "mobile-accessories": "smartphones",
    "mobile accessories": "smartphones",
    "mobiles-tablets": "smartphones",
    "power banks": "smartphones",
    # Laptops & Computers
    "laptops": "laptops",
    "entry-level-laptops": "laptops",
    "premium-laptops": "laptops",
    "gaming-laptops": "laptops",
    "tablets": "tablets",
    "regular-tablets": "tablets",
    "monitors": "laptops",
    "printers": "laptops",
    "computers": "laptops",
    "pen-drives": "laptops",
    "hard-drives": "laptops",
    "routers": "laptops",
    "keyboards": "laptops",
    # Audio
    "headphones-headsets": "audio",
    "headphones": "audio",
    "true-wireless": "audio",
    "bluetooth-wifi-speakers": "audio",
    "bluetooth speakers": "audio",
    "tv-speakers-soundbars": "audio",
    "soundbars": "audio",
    "home-audio": "audio",
    "party speakers": "audio",
    # Wearables
    "smart-watches": "smartwatches",
    "smart-devices": "smartwatches",
    "fitness-bands": "smartwatches",
    # Cameras
    "cameras": "cameras",
    "action-cameras": "cameras",
    "dslr": "cameras",
    # TVs
    "televisions": "televisions",
    "led-televisions": "televisions",
    "led tvs": "televisions",
    "smart tvs": "televisions",
    "projectors": "televisions",
    "streaming devices": "televisions",
    # Large Appliances
    "refrigerators": "refrigerators",
    "frost-free": "refrigerators",
    "washing-machines": "washing-machines",
    "split-air-conditioners": "air-conditioners",
    "air-conditioners": "air-conditioners",
    "air-care": "air-conditioners",
    "microwave-ovens": "appliances",
    "dishwashers": "appliances",
    "water-heaters": "appliances",
    # Small Appliances
    "air-purifiers": "appliances",
    "water-purifiers": "appliances",
    "vacuum-cleaners": "appliances",
    "fans": "appliances",
    "irons": "appliances",
    "home-appliances": "appliances",
    # Kitchen
    "kitchen-appliances": "kitchen-tools",
    "mixer-grinders": "kitchen-tools",
    "air-fryers": "kitchen-tools",
    "coffee-machines": "kitchen-tools",
    "induction-cooktops": "kitchen-tools",
    "electric-kettles": "kitchen-tools",
    "juicers": "kitchen-tools",
    "food-processors": "kitchen-tools",
    # Personal Care
    "personal-care": "grooming",
    "trimmers": "grooming",
    "shavers": "grooming",
    "hair-dryers": "grooming",
    # Gaming
    "gaming": "gaming",
    "gaming-consoles": "gaming",
    "gaming-accessories": "gaming",
}

# ---------------------------------------------------------------------------
# Seed URLs — using collection pages (more reliable SSR than /products/ pages)
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 15  # pages for top categories
_STD = 8   # pages for standard categories

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones ─────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l3_categories=smart-phones&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l3_categories=feature-phones&department=electronics", _STD),
    ("https://www.reliancedigital.in/products/?l3_categories=regular-tablets&department=electronics", _STD),
    # ── Laptops & Computers ─────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l3_categories=entry-level-laptops&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l3_categories=premium-laptops&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l2_category=monitors&department=electronics", _STD),
    ("https://www.reliancedigital.in/products/?l2_category=printers&department=electronics", _STD),
    # ── TVs ─────────────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l3_categories=led-televisions&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l2_category=projectors&department=electronics", _STD),
    # ── Audio ───────────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l3_categories=true-wireless&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l3_categories=bluetooth-wifi-speakers&department=electronics", _STD),
    ("https://www.reliancedigital.in/products/?l3_categories=tv-speakers-soundbars&department=electronics", _STD),
    # ── Wearables ───────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=smart-devices&department=electronics", _TOP),
    # ── Cameras ─────────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=cameras&department=electronics", _STD),
    # ── Large Appliances ────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=refrigerators&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l3_categories=washing-machines&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l3_categories=split-air-conditioners&department=electronics", _TOP),
    ("https://www.reliancedigital.in/products/?l2_category=air-care&department=electronics", _STD),
    # ── Small/Kitchen Appliances ────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=kitchen-appliances&department=electronics", _STD),
    ("https://www.reliancedigital.in/products/?l2_category=home-appliances&department=electronics", _STD),
    # ── Personal Care ───────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=personal-care&department=electronics", _STD),
    # ── Gaming ──────────────────────────────────────────────────────────
    ("https://www.reliancedigital.in/products/?l2_category=gaming&department=electronics", _STD),
]

MAX_LISTING_PAGES = 5
PAGE_SIZE = 12


class RelianceDigitalSpider(BaseWhydudSpider):
    """Scrapes RelianceDigital.in electronics store.

    Reliance Digital uses Fynd/Jio Commerce Platform (Vue.js 2 SPA).
    Product data is embedded in window.__INITIAL_STATE__ as JSON:
    - productListingPage.productlists.items[] for listings
    - productDetailsPage.product for product details

    Prices in the JSON are in INR (rupees), NOT paisa.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "reliance_digital"
    allowed_domains = ["reliancedigital.in", "www.reliancedigital.in"]

    QUICK_MODE_CATEGORIES = 6

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 6,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
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
        self._category_urls: list[str] = (
            [u.strip() for u in category_urls.split(",") if u.strip()]
            if category_urls
            else []
        )
        self._max_pages_override: int | None = int(max_pages) if max_pages else None
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Reliance Digital spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Stealth helpers
    # ------------------------------------------------------------------

    async def _apply_stealth(self, page, request):
        """Apply playwright-stealth scripts before navigation."""
        try:
            await self.STEALTH.apply_stealth_async(page)
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(45000)
        except Exception as e:
            self.logger.warning(f"Stealth setup issue: {e}")

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit requests for category listing pages."""
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = self._strip_page_params(url)
            self._max_pages_map[base] = max_pg

            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": self._resolve_category_from_url(url),
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories")

    def _load_urls(self) -> list[tuple[str, int]]:
        """Resolve the (url, max_pages) list to crawl."""
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}")
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_CATEGORIES} categories "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[:self.QUICK_MODE_CATEGORIES]
                ]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _strip_page_params(self, url: str) -> str:
        """Remove page_no and page_size parameters from URL."""
        base = re.sub(r"[?&]page_no=\d+", "", url)
        base = re.sub(r"[?&]page_size=\d+", "", base)
        return base.rstrip("?&")

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path/params."""
        url_lower = url.lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword.replace(" ", "-") in url_lower:
                return slug
        return None

    def _extract_initial_state(self, response) -> dict | None:
        """Extract window.__INITIAL_STATE__ JSON from page source."""
        match = re.search(
            r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*;?\s*</script>",
            response.text,
            re.DOTALL,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"Failed to parse __INITIAL_STATE__ on {response.url}")
            return None

    def _parse_price_rupees(self, value) -> Decimal | None:
        """Parse a price value (in rupees) to Decimal in paisa."""
        if value is None:
            return None
        try:
            rupees = Decimal(str(value))
            if rupees <= 0:
                return None
            return rupees * 100  # convert to paisa
        except (InvalidOperation, ValueError, TypeError):
            return None

    def _is_blocked(self, response) -> bool:
        """Detect if site served a block/error page."""
        if response.status in (403, 429):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from listing page via __INITIAL_STATE__."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Extract from __INITIAL_STATE__
        data = self._extract_initial_state(response)
        products = []
        if data:
            plp = data.get("productListingPage") or {}
            pl = plp.get("productlists") or {}
            items = pl.get("items") or []
            if isinstance(items, list):
                products = items

        if products:
            self.logger.info(f"Found {len(products)} products on {response.url}")
            for prod in products:
                slug = prod.get("slug", "")
                if not slug:
                    continue
                product_url = f"https://www.reliancedigital.in/product/{slug}"
                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "category_slug": category_slug,
                        "listing_data": prod,
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "domcontentloaded"),
                            PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                        ],
                    },
                )
        else:
            # Try HTML fallback — look for product cards/links
            links = response.css("a[href*='/product/']::attr(href)").getall()
            seen = set()
            for href in links:
                full_url = response.urljoin(href)
                if full_url not in seen and "/product/" in full_url:
                    seen.add(full_url)
                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_product_page,
                        errback=self.handle_error,
                        headers=self._make_headers(),
                        meta={
                            "category_slug": category_slug,
                            "playwright": True,
                            "playwright_page_init_callback": self._apply_stealth,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "domcontentloaded"),
                                PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                            ],
                        },
                    )
            if not links:
                self.logger.warning(f"No products found on {response.url}")
                return

        # Pagination
        base_url = self._strip_page_params(response.url)
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page_no={next_page}&page_size={PAGE_SIZE}"
            self._pages_followed[base_url] = next_page

            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page."""
        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: __INITIAL_STATE__ → productDetailsPage
        data = self._extract_initial_state(response)
        if data:
            pdp = data.get("productDetailsPage") or {}
            product = pdp.get("product")
            if product and product.get("name"):
                item = self._parse_from_state(product, response.url, category_slug)
                if item:
                    self._product_pages_scraped += 1
                    self._products_extracted += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # Extraction: __INITIAL_STATE__ (primary)
    # ------------------------------------------------------------------

    def _parse_from_state(
        self, product: dict, url: str, category_slug: str | None,
    ) -> ProductItem | None:
        """Extract product data from __INITIAL_STATE__.productDetailsPage.product."""
        name = product.get("name")
        if not name:
            return None

        uid = product.get("uid")
        if not uid:
            return None
        external_id = str(uid)

        # Prices — in rupees, convert to paisa
        price_data = product.get("price") or {}
        selling_price = self._parse_price_rupees(
            (price_data.get("effective") or {}).get("min")
            or (price_data.get("selling") or {}).get("min")
        )
        mrp = self._parse_price_rupees(
            (price_data.get("marked") or {}).get("min")
        )

        # Brand
        brand_data = product.get("brand") or {}
        brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data)

        # Images
        images = []
        for media in product.get("medias") or []:
            img_url = media.get("url", "")
            if img_url and media.get("type") == "image":
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                images.append(img_url)

        # Specs from attributes
        specs = {}
        attrs = product.get("attributes") or {}
        for key, val in attrs.items():
            if key and val and str(val).strip():
                specs[key.replace("_", " ").title()] = str(val)

        # Grouped attributes for additional specs
        for group in product.get("grouped_attributes") or []:
            for detail in group.get("details") or []:
                key = detail.get("key", "")
                val = detail.get("value", "")
                if key and val and key not in specs:
                    specs[key] = str(val)

        # Rating
        rating = None
        review_count = None
        rating_val = product.get("rating")
        if rating_val and str(rating_val) not in ("0", "0.0", "null", "None"):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = product.get("rating_count")
        if count_val and str(count_val) not in ("0", "null", "None"):
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = product.get("is_available", True) and product.get("sellable", True)

        # Categories
        if not category_slug:
            cat_map = product.get("category_map") or {}
            for level in ("l3", "l2", "l1"):
                cat_name = (cat_map.get(level) or {}).get("name", "").lower()
                for kw, slug in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_name.replace(" ", "-"):
                        category_slug = slug
                        break
                if category_slug:
                    break

        # Breadcrumbs
        breadcrumbs = []
        cat_map = product.get("category_map") or {}
        for level in ("l1", "l2", "l3"):
            cat_name = (cat_map.get(level) or {}).get("name")
            if cat_name:
                breadcrumbs.append(cat_name)

        # Description
        description = product.get("description") or product.get("short_description")

        # Warranty
        warranty = attrs.get("warranty") or specs.get("Warranty")

        # Model
        model_number = attrs.get("model") or specs.get("Model")

        # Weight/Dimensions from grouped_attributes
        weight = specs.get("Weight") or specs.get("Product Weight") or specs.get("Net Weight")
        dimensions = specs.get("Dimensions") or specs.get("Product Dimensions")

        slug = product.get("slug", "")
        product_url = f"https://www.reliancedigital.in/product/{slug}" if slug else url

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=product_url,
            title=name,
            brand=brand if brand else None,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name="Reliance Digital",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="Reliance Digital",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=warranty,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=specs.get("Country Of Origin"),
            manufacturer=specs.get("Manufacturer") or brand,
            model_number=model_number,
            weight=weight,
            dimensions=dimensions,
        )

    # ------------------------------------------------------------------
    # Extraction: JSON-LD (fallback)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self, response, category_slug: str | None,
    ) -> ProductItem | None:
        """Extract product data from JSON-LD structured data."""
        ld_scripts = response.css('script[type="application/ld+json"]::text').getall()
        for script_text in ld_scripts:
            try:
                ld_data = json.loads(script_text)
            except (json.JSONDecodeError, ValueError):
                continue

            if isinstance(ld_data, list):
                for item in ld_data:
                    if item.get("@type") == "Product":
                        ld_data = item
                        break
                else:
                    continue

            if ld_data.get("@type") != "Product":
                continue

            name = ld_data.get("name")
            if not name:
                continue

            product_id = ld_data.get("productID")
            if not product_id:
                # Try to extract from URL
                match = PRODUCT_UID_RE.search(response.url)
                product_id = match.group(1) if match else None
            if not product_id:
                continue

            offers = ld_data.get("offers") or {}
            price = self._parse_price_rupees(offers.get("price"))

            brand_data = ld_data.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data) if brand_data else None

            images = ld_data.get("image") or []
            if isinstance(images, str):
                images = [images]

            rating = None
            review_count = None
            agg_rating = ld_data.get("aggregateRating") or {}
            if agg_rating.get("ratingValue"):
                try:
                    rating = Decimal(str(agg_rating["ratingValue"]))
                except (InvalidOperation, ValueError):
                    pass
            if agg_rating.get("ratingCount"):
                try:
                    review_count = int(agg_rating["ratingCount"])
                except (ValueError, TypeError):
                    pass

            in_stock = True
            availability = offers.get("availability", "")
            if "OutOfStock" in availability:
                in_stock = False

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(product_id),
                url=response.url,
                title=name,
                brand=brand,
                price=price,
                mrp=None,
                images=images,
                rating=rating,
                review_count=review_count,
                specs={},
                seller_name="Reliance Digital",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="Reliance Digital",
                category_slug=category_slug,
                about_bullets=[],
                offer_details=[],
                raw_html_path=None,
                description=ld_data.get("description"),
                warranty=None,
                delivery_info=None,
                return_policy=None,
                breadcrumbs=[],
                variant_options=[],
                country_of_origin=None,
                manufacturer=None,
                model_number=None,
                weight=None,
                dimensions=None,
            )
        return None
