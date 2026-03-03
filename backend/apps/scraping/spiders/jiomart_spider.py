"""JioMart spider — scrapes multi-category marketplace listings and details.

Architecture:
  JioMart runs on Jio Commerce Platform (similar to Reliance Digital).
  - Cloudflare protected — Playwright required for all pages
  - Data source: window.__INITIAL_STATE__ or API endpoints
  - JSON-LD Product schema on detail pages
  - Skip grocery/perishable categories

URL patterns:
  Category: /c/{category-path}/{category-id}
  Product:  /p/{category}/{product-slug}/{product-id}
  Search:   /search/{query}
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

PRODUCT_ID_RE = re.compile(r"/(\d{6,})(?:\?|$)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "jiomart"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Electronics
    "smartphones": "smartphones",
    "mobiles": "smartphones",
    "mobile-phones": "smartphones",
    "mobile-accessories": "smartphones",
    "power-banks": "smartphones",
    "tablets": "tablets",
    "laptops": "laptops",
    "computers": "laptops",
    "monitors": "laptops",
    "printers": "laptops",
    "headphones": "audio",
    "earphones": "audio",
    "speakers": "audio",
    "soundbars": "audio",
    "televisions": "televisions",
    "smart-tv": "televisions",
    "cameras": "cameras",
    "smartwatches": "smartwatches",
    "smart-watches": "smartwatches",
    # Appliances
    "refrigerators": "refrigerators",
    "washing-machines": "washing-machines",
    "air-conditioners": "air-conditioners",
    "microwave": "appliances",
    "water-purifiers": "appliances",
    "air-purifiers": "appliances",
    "vacuum-cleaners": "appliances",
    "fans": "appliances",
    # Kitchen
    "mixer-grinders": "kitchen-tools",
    "air-fryers": "kitchen-tools",
    "electric-kettles": "kitchen-tools",
    "induction-cooktops": "kitchen-tools",
    "kitchen-appliances": "kitchen-tools",
    # Fashion
    "mens-clothing": "mens-fashion",
    "mens-tshirts": "mens-fashion",
    "mens-shirts": "mens-fashion",
    "womens-clothing": "womens-fashion",
    "womens-kurtas": "womens-fashion",
    "sarees": "womens-fashion",
    "kids-clothing": "kids-fashion",
    # Footwear
    "mens-footwear": "footwear",
    "womens-footwear": "footwear",
    "sports-shoes": "footwear",
    # Personal Care
    "personal-care": "grooming",
    "trimmers": "grooming",
    "shavers": "grooming",
    "hair-dryers": "grooming",
    # Home
    "home-furnishing": "home-decor",
    "home-decor": "home-decor",
    "bedsheets": "home-decor",
}

# ---------------------------------------------------------------------------
# Seed URLs — JioMart category pages (skip grocery/perishables)
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Electronics ─────────────────────────────────────────────────────
    ("https://www.jiomart.com/c/electronics/mobiles-tablets/smartphones/476", _TOP),
    ("https://www.jiomart.com/c/electronics/mobiles-tablets/tablets/477", _STD),
    ("https://www.jiomart.com/c/electronics/laptops-desktops/laptops/480", _TOP),
    ("https://www.jiomart.com/c/electronics/televisions/smart-tv/486", _STD),
    ("https://www.jiomart.com/c/electronics/audio-video/headphones-earphones/490", _TOP),
    ("https://www.jiomart.com/c/electronics/audio-video/bluetooth-speakers/491", _STD),
    ("https://www.jiomart.com/c/electronics/cameras-accessories/cameras/494", _STD),
    ("https://www.jiomart.com/c/electronics/wearable-devices/smartwatches/498", _STD),
    # ── Home Appliances ─────────────────────────────────────────────────
    ("https://www.jiomart.com/c/home-appliances/large-appliances/refrigerators/506", _STD),
    ("https://www.jiomart.com/c/home-appliances/large-appliances/washing-machines/507", _STD),
    ("https://www.jiomart.com/c/home-appliances/large-appliances/air-conditioners/508", _STD),
    ("https://www.jiomart.com/c/home-appliances/small-appliances/air-purifiers/513", _STD),
    ("https://www.jiomart.com/c/home-appliances/small-appliances/vacuum-cleaners/514", _STD),
    # ── Kitchen Appliances ──────────────────────────────────────────────
    ("https://www.jiomart.com/c/home-appliances/kitchen-appliances/mixer-grinders/517", _STD),
    ("https://www.jiomart.com/c/home-appliances/kitchen-appliances/air-fryers/520", _STD),
    # ── Fashion ─────────────────────────────────────────────────────────
    ("https://www.jiomart.com/c/fashion/mens-clothing/t-shirts/550", _STD),
    ("https://www.jiomart.com/c/fashion/mens-clothing/shirts/551", _STD),
    ("https://www.jiomart.com/c/fashion/womens-clothing/kurtas-kurtis/560", _STD),
    ("https://www.jiomart.com/c/fashion/womens-clothing/sarees/561", _STD),
    # ── Personal Care ───────────────────────────────────────────────────
    ("https://www.jiomart.com/c/premium-beauty/skincare/moisturizers/587", _STD),
    ("https://www.jiomart.com/c/premium-beauty/makeup/face/591", _STD),
    # ── Home Furnishing ─────────────────────────────────────────────────
    ("https://www.jiomart.com/c/home-kitchen/home-furnishing/bedsheets/610", _STD),
]

MAX_LISTING_PAGES = 5


class JioMartSpider(BaseWhydudSpider):
    """Scrapes JioMart.com multi-category marketplace.

    JioMart is Cloudflare-protected — Playwright required for all pages.
    Uses Jio Commerce Platform similar to Reliance Digital.

    Data extraction:
    - window.__INITIAL_STATE__ for listing and detail data
    - JSON-LD Product schema on detail pages as fallback
    - HTML CSS selectors as last resort

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "jiomart"
    allowed_domains = ["jiomart.com", "www.jiomart.com"]

    QUICK_MODE_CATEGORIES = 5

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
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
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"JioMart spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Stealth
    # ------------------------------------------------------------------

    async def _apply_stealth(self, page, request):
        try:
            await self.STEALTH.apply_stealth_async(page)
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(45000)
        except Exception as e:
            self.logger.warning(f"Stealth setup issue: {e}")

    # ------------------------------------------------------------------
    # start_requests — Playwright required (Cloudflare)
    # ------------------------------------------------------------------

    def start_requests(self):
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("?")[0]
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
                        PageMethod("wait_for_timeout", random.randint(3000, 5000)),
                    ],
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (Playwright)")

    def _load_urls(self) -> list[tuple[str, int]]:
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(f"Running for job {self.job_id}")
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[:self.QUICK_MODE_CATEGORIES]
                ]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_category_from_url(self, url: str) -> str | None:
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None

    def _extract_initial_state(self, response) -> dict | None:
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

    def _parse_price(self, price_val) -> Decimal | None:
        if price_val is None:
            return None
        try:
            val_str = str(price_val).replace(",", "")
            match = PRICE_RE.search(val_str)
            if not match:
                return None
            rupees = Decimal(match.group().replace(",", ""))
            if rupees <= 0:
                return None
            return rupees * 100
        except (InvalidOperation, ValueError):
            return None

    def _is_blocked(self, response) -> bool:
        if response.status in (403, 429, 503):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "just a moment" in title or "attention required" in title:
            return True
        if "access denied" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: __INITIAL_STATE__
        state = self._extract_initial_state(response)
        products = []
        if state:
            plp = state.get("productListingPage") or {}
            pl = plp.get("productlists") or {}
            items = pl.get("items") or []
            if isinstance(items, list):
                products = items

        if products:
            self.logger.info(f"Found {len(products)} products on {response.url}")
            for prod in products:
                slug = prod.get("slug") or prod.get("url", "")
                if not slug:
                    continue
                product_url = response.urljoin(slug) if slug.startswith("/") else f"https://www.jiomart.com/p/{slug}"
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
            # Strategy 2: HTML links
            links = set()
            for href in response.css("a[href*='/p/']::attr(href)").getall():
                full_url = response.urljoin(href)
                if "/p/" in full_url:
                    links.add(full_url)
            if links:
                self.logger.info(f"Found {len(links)} products (HTML) on {response.url}")
                for prod_url in links:
                    yield scrapy.Request(
                        prod_url,
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
            else:
                self.logger.warning(f"No products found on {response.url}")
                return

        # Pagination
        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page={next_page}"
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
                        PageMethod("wait_for_timeout", random.randint(3000, 5000)),
                    ],
                },
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        # Strategy 1: __INITIAL_STATE__
        state = self._extract_initial_state(response)
        if state:
            pdp = state.get("productDetailsPage") or {}
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

        # Strategy 3: Listing data fallback
        if listing_data:
            item = self._parse_from_listing(listing_data, response.url, category_slug)
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

    def _parse_from_state(self, product: dict, url: str, category_slug: str | None) -> ProductItem | None:
        name = product.get("name")
        if not name:
            return None

        uid = product.get("uid") or product.get("item_code")
        if not uid:
            return None
        external_id = str(uid)

        # Prices (rupees → paisa)
        price_data = product.get("price") or {}
        selling_price = self._parse_price(
            (price_data.get("effective") or {}).get("min")
            or (price_data.get("selling") or {}).get("min")
        )
        mrp = self._parse_price((price_data.get("marked") or {}).get("min"))

        brand_data = product.get("brand") or {}
        brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data) if brand_data else None

        images = []
        for media in product.get("medias") or []:
            img_url = media.get("url", "")
            if img_url and media.get("type") == "image":
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                images.append(img_url)

        specs = {}
        for key, val in (product.get("attributes") or {}).items():
            if key and val:
                specs[key.replace("_", " ").title()] = str(val)

        rating = None
        if product.get("rating"):
            try:
                rating = Decimal(str(product["rating"]))
            except (InvalidOperation, ValueError):
                pass

        in_stock = product.get("is_available", True)
        description = product.get("description")

        if not category_slug:
            cat_map = product.get("category_map") or {}
            for level in ("l3", "l2"):
                cat_name = (cat_map.get(level) or {}).get("name", "").lower().replace(" ", "-")
                for kw, slug in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_name:
                        category_slug = slug
                        break
                if category_slug:
                    break

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=None,
            specs=specs,
            seller_name="JioMart",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="JioMart",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=specs.get("Warranty"),
            delivery_info=None,
            return_policy=None,
            breadcrumbs=[],
            variant_options=[],
            country_of_origin=specs.get("Country Of Origin"),
            manufacturer=specs.get("Manufacturer") or brand,
            model_number=specs.get("Model"),
            weight=specs.get("Weight"),
            dimensions=specs.get("Dimensions"),
        )

    # ------------------------------------------------------------------
    # Extraction: JSON-LD (fallback)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(self, response, category_slug: str | None) -> ProductItem | None:
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
            sku = ld_data.get("sku") or ld_data.get("productID")
            if not name or not sku:
                continue

            offers = ld_data.get("offers") or {}
            if isinstance(offers, list) and offers:
                offers = offers[0]
            price = self._parse_price(offers.get("price"))

            brand_data = ld_data.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else None

            images = ld_data.get("image") or []
            if isinstance(images, str):
                images = [images]

            in_stock = "InStock" in (offers.get("availability") or "")

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url,
                title=name,
                brand=brand,
                price=price,
                mrp=None,
                images=images,
                rating=None,
                review_count=None,
                specs={},
                seller_name="JioMart",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="JioMart",
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
                manufacturer=brand,
                model_number=None,
                weight=None,
                dimensions=None,
            )
        return None

    # ------------------------------------------------------------------
    # Extraction: Listing data fallback
    # ------------------------------------------------------------------

    def _parse_from_listing(self, listing: dict, url: str, category_slug: str | None) -> ProductItem | None:
        name = listing.get("name")
        uid = listing.get("uid") or listing.get("item_code")
        if not name or not uid:
            return None

        price_data = listing.get("price") or {}
        selling_price = self._parse_price((price_data.get("effective") or {}).get("min"))
        mrp = self._parse_price((price_data.get("marked") or {}).get("min"))

        brand_data = listing.get("brand") or {}
        brand = brand_data.get("name") if isinstance(brand_data, dict) else None

        images = []
        for media in listing.get("medias") or []:
            if media.get("type") == "image":
                images.append(media.get("url", ""))

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=str(uid),
            url=url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=[img for img in images if img],
            rating=None,
            review_count=None,
            specs={},
            seller_name="JioMart",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="JioMart",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=None,
            warranty=None,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=[],
            variant_options=[],
            country_of_origin=None,
            manufacturer=brand,
            model_number=None,
            weight=None,
            dimensions=None,
        )
