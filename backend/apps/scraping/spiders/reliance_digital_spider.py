"""Reliance Digital spider — scrapes products via the open Fynd Commerce JSON API.

Architecture:
  Single-phase: the /ext/raven-api/catalog/v1.0/products endpoint returns full
  product data (title, brand, price, images, specs) in one JSON response.
  No Playwright needed — pure HTTP + JSON.

  Prices in the API are in RUPEES (not paisa). Spider converts to paisa (* 100).

API details:
  Endpoint: GET https://www.reliancedigital.in/ext/raven-api/catalog/v1.0/products
  Params:   q={query}&page={n}&pageSize=24
  Auth:     None required (open API)
  Pagination: response.page.current, response.page.has_next, response.page.item_total
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

MARKETPLACE_SLUG = "reliance-digital"

API_BASE = "https://www.reliancedigital.in/ext/raven-api/catalog/v1.0/products"
PAGE_SIZE = 24

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


class RelianceDigitalSpider(BaseWhydudSpider):
    """Scrapes RelianceDigital.in via their open Fynd Commerce JSON API.

    No Playwright required — pure HTTP requests returning JSON.

    Prices in the API are in INR (rupees), NOT paisa. Spider converts to paisa.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override query terms or API URLs.
      max_pages     — override max pages per query.
    """

    name = "reliance_digital"
    allowed_domains = ["reliancedigital.in", "www.reliancedigital.in"]

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

        # Stats
        self._api_pages_fetched: int = 0
        self._products_extracted: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        self.logger.info(
            f"Reliance Digital API spider finished ({reason}): "
            f"api_pages={self._api_pages_fetched}, "
            f"products_extracted={self._products_extracted}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    def _api_headers(self) -> dict[str, str]:
        """Build minimal headers for the JSON API."""
        return {
            "User-Agent": self._random_ua(),
            "Accept": "application/json",
            "Accept-Language": "en-IN,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }

    @staticmethod
    def _build_api_url(query: str, page: int) -> str:
        """Construct the API URL for a search query and page number."""
        q = query.replace(" ", "%20")
        return f"{API_BASE}?q={q}&page={page}&pageSize={PAGE_SIZE}"

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit API requests for each seed query."""
        queries = self._load_queries()
        random.shuffle(queries)

        for query, category_slug, max_pg in queries:
            url = self._build_api_url(query, 1)
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
    # API response parsing
    # ------------------------------------------------------------------

    def parse_api_response(self, response):
        """Parse the JSON API response and yield ProductItems."""
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

        # Extract products from response
        items = data.get("items") or []
        if not items:
            self.logger.info(
                f"No products on page {current_page} for '{query}' — stopping"
            )
            return

        self.logger.info(
            f"Query '{query}' page {current_page}: {len(items)} products"
        )

        for product in items:
            item = self._parse_product(product, category_slug)
            if item:
                self._products_extracted += 1
                self.items_scraped += 1
                yield item

        # Pagination — follow if has_next and within page limit
        page_info = data.get("page") or {}
        has_next = page_info.get("has_next", False)

        if has_next and current_page < max_pages:
            next_page = current_page + 1
            next_url = self._build_api_url(query, next_page)
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

    # ------------------------------------------------------------------
    # Product extraction from API JSON
    # ------------------------------------------------------------------

    def _parse_product(self, product: dict, category_slug: str) -> ProductItem | None:
        """Extract a ProductItem from a single API product object."""
        name = product.get("name")
        uid = product.get("uid")
        if not name or not uid:
            return None

        external_id = str(uid)

        # Prices — API returns in rupees, convert to paisa
        price_data = product.get("price") or {}
        effective = self._price_to_paisa(
            (price_data.get("effective") or {}).get("min")
        )
        marked = self._price_to_paisa(
            (price_data.get("marked") or {}).get("min")
        )

        # Brand
        brand_data = product.get("brand") or {}
        brand = brand_data.get("name", "") if isinstance(brand_data, dict) else ""

        # URL construction
        slug = product.get("slug", "")
        url = f"https://www.reliancedigital.in/{slug}/p/{uid}" if slug else ""
        if not url:
            return None

        # Images from medias array
        images = []
        for media in product.get("medias") or []:
            img_url = media.get("url", "")
            if img_url:
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                images.append(img_url)

        # Specs from attributes — only consumer-facing fields
        specs = {}
        attrs = product.get("attributes") or {}
        # Map of API attribute key → display label
        spec_keys = {
            # Identifiers
            "ean": "EAN",
            "model": "Model",
            "model-name": "Model Name",
            "series": "Series",
            # Storage & Memory
            "internal-storage": "Internal Storage",
            "ram": "RAM",
            "storage": "Storage",
            # Display
            "display_type": "Display Type",
            "screen_size_diagonal": "Screen Size",
            "screen_resolution": "Screen Resolution",
            "resolution": "Resolution",
            "refresh_rate": "Refresh Rate",
            # Processor & Performance
            "processor": "Processor",
            "graphics": "Graphics",
            # Camera
            "camera": "Camera",
            "front_camera": "Front Camera",
            "rear_camera": "Rear Camera",
            "selfie_camera": "Front Camera",
            # Battery & Power
            "battery_capacity": "Battery Capacity",
            "standby_time": "Standby Time",
            "talk_time": "Talk Time",
            "wattage": "Wattage",
            # Connectivity
            "operating_system": "Operating System",
            "cellular_technology": "Network",
            "sim_type": "SIM Type",
            "bluetooth": "Bluetooth",
            "bluetooth_version": "Bluetooth Version",
            "wi_fi": "Wi-Fi",
            "wi-fi": "Wi-Fi",
            "hdmi": "HDMI",
            "usb": "USB",
            "connectivity": "Connectivity",
            "nfc": "NFC",
            # Audio & Media
            "audio_formats": "Audio Formats",
            "video_formats": "Video Formats",
            "noise_cancellation": "Noise Cancellation",
            "driver_size": "Driver Size",
            "impedance": "Impedance",
            "frequency_response": "Frequency Response",
            "microphone": "Microphone",
            # Physical
            "color": "Color",
            "colour": "Color",
            "net-weight": "Weight",
            "weight": "Weight",
            "item-weight": "Weight",
            "dimensions": "Dimensions",
            "water_resistant": "Water Resistant",
            "fingerprint_recognition": "Fingerprint",
            "sensors": "Sensors",
            # Appliance-specific
            "capacity": "Capacity",
            "energy_rating": "Energy Rating",
            "star_rating": "Star Rating",
            # Meta
            "warranty": "Warranty",
            "country_of_origin": "Country of Origin",
            "country-of-origin": "Country of Origin",
            "manufacturer": "Manufacturer",
            "in_the_box": "In The Box",
            "in-the-box": "In The Box",
        }
        for api_key, display_key in spec_keys.items():
            val = attrs.get(api_key)
            if val and isinstance(val, (str, int, float)) and str(val).strip():
                specs[display_key] = str(val).strip()

        # Dimensions from individual item-height/width/length
        if "Dimensions" not in specs:
            h = attrs.get("item-height", "")
            w = attrs.get("item-width", "")
            l = attrs.get("item-length", "")
            parts = [f"{v}" for v in (l, w, h) if v]
            if len(parts) >= 2:
                specs["Dimensions"] = " x ".join(parts)

        # Grouped attributes — these are already curated by Fynd
        for group in product.get("grouped_attributes") or []:
            for detail in group.get("details") or []:
                key = detail.get("key", "")
                val = detail.get("value", "")
                if key and val and isinstance(val, (str, int, float)) and key not in specs:
                    specs[key] = str(val)

        # Stock
        in_stock = product.get("sellable", True)

        # Categories from API
        resolved_category = category_slug
        if not resolved_category:
            categories = product.get("categories") or []
            for cat in categories:
                cat_name = (cat.get("name") or "").lower()
                for kw, slug_val in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_name:
                        resolved_category = slug_val
                        break
                if resolved_category:
                    break

        # Breadcrumbs from categories
        breadcrumbs = [
            cat.get("name", "")
            for cat in (product.get("categories") or [])
            if cat.get("name")
        ]

        # Country of origin — top-level field takes precedence
        country = (
            product.get("country_of_origin")
            or attrs.get("country_of_origin")
            or attrs.get("country-of-origin")
        )

        # Description — attrs.description is HTML, strip tags for clean text
        raw_desc = attrs.get("description") or attrs.get("product_details") or ""
        description = self._strip_html(raw_desc) if raw_desc else None

        # About bullets — key-features contains <li> items
        about_bullets = []
        key_features = attrs.get("key-features") or ""
        if key_features:
            about_bullets = re.findall(r"<li>(.*?)</li>", key_features, re.DOTALL)
            about_bullets = [self._strip_html(b).strip() for b in about_bullets if b.strip()]

        # Warranty
        warranty = attrs.get("warranty") or specs.get("Warranty")

        # Weight
        weight = (
            specs.get("Weight")
            or attrs.get("net-weight")
            or attrs.get("item-weight")
            or attrs.get("weight")
        )

        # Model
        model_number = attrs.get("model") or attrs.get("model-name") or attrs.get("manufacturer-part-number")

        # Manufacturer
        manufacturer = attrs.get("manufacturer") or brand

        # Item code as SKU in specs
        item_code = product.get("item_code")
        if item_code:
            specs["SKU"] = str(item_code)

        # Discount string
        discount = product.get("discount")
        if discount:
            specs["Discount"] = str(discount)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=url,
            title=name,
            brand=brand if brand else None,
            price=effective,
            mrp=marked,
            images=images,
            rating=None,
            review_count=None,
            specs=specs,
            seller_name="Reliance Digital",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="Reliance Digital",
            category_slug=resolved_category or None,
            about_bullets=about_bullets,
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=warranty,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=str(country) if country else None,
            manufacturer=str(manufacturer) if manufacturer else None,
            model_number=str(model_number) if model_number else None,
            weight=str(weight) if weight else None,
            dimensions=specs.get("Dimensions"),
        )

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
