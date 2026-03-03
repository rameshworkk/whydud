"""Croma.com spider — scrapes product listings and detail pages.

Architecture:
  Croma is a React SPA with server-side rendered data in window.__INITIAL_DATA__.
  - Listing pages: plpReducer contains product arrays (HTTP, no Playwright needed)
  - Detail pages: pdpReducer contains full product data (HTTP, no Playwright needed)
  - Fallback: Playwright for pages where __INITIAL_DATA__ is incomplete
  - JSON-LD structured data available on detail pages as secondary source

URL patterns:
  Category: /category-name/subcategory/c/{numeric_id}?page={n}
  Product:  /{product-slug}/p/{product_code}
  Search:   /searchB?q={keyword}&page={n}
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

PRODUCT_CODE_RE = re.compile(r"/p/(\d+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "croma"

# ---------------------------------------------------------------------------
# Croma search keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Smartphones & Accessories
    "smartphones": "smartphones",
    "mobile phones": "smartphones",
    "mobile accessories": "smartphones",
    "power banks": "smartphones",
    "mobile chargers": "smartphones",
    "phone cases": "smartphones",
    # Laptops & Computers
    "laptops": "laptops",
    "gaming laptops": "laptops",
    "chromebooks": "laptops",
    "tablets": "tablets",
    "monitors": "laptops",
    "printers": "laptops",
    "routers": "laptops",
    "hard drives": "laptops",
    "pen drives": "laptops",
    "keyboards": "laptops",
    "mouse": "laptops",
    # Audio
    "headphones": "audio",
    "earbuds": "audio",
    "earphones": "audio",
    "bluetooth speakers": "audio",
    "soundbars": "audio",
    "home theatre": "audio",
    "party speakers": "audio",
    # Wearables
    "smartwatches": "smartwatches",
    "fitness bands": "smartwatches",
    # Cameras
    "cameras": "cameras",
    "action cameras": "cameras",
    "dslr cameras": "cameras",
    "mirrorless cameras": "cameras",
    "camera accessories": "cameras",
    # TVs & Entertainment
    "televisions": "televisions",
    "led tvs": "televisions",
    "smart tvs": "televisions",
    "projectors": "televisions",
    "streaming devices": "televisions",
    # Large Appliances
    "refrigerators": "refrigerators",
    "washing machines": "washing-machines",
    "air conditioners": "air-conditioners",
    "microwave ovens": "appliances",
    "dishwashers": "appliances",
    "water heaters": "appliances",
    "geysers": "appliances",
    "chimneys": "appliances",
    # Small Appliances
    "air purifiers": "appliances",
    "water purifiers": "appliances",
    "vacuum cleaners": "appliances",
    "robot vacuum": "appliances",
    "fans": "appliances",
    "room heaters": "appliances",
    "irons": "appliances",
    # Kitchen Appliances
    "mixer grinders": "kitchen-tools",
    "air fryers": "kitchen-tools",
    "coffee machines": "kitchen-tools",
    "induction cooktops": "kitchen-tools",
    "electric kettles": "kitchen-tools",
    "juicers": "kitchen-tools",
    "toasters": "kitchen-tools",
    "food processors": "kitchen-tools",
    "rice cookers": "kitchen-tools",
    "oven toaster grills": "kitchen-tools",
    "gas stoves": "kitchen-tools",
    "hobs": "kitchen-tools",
    # Personal Care
    "trimmers": "grooming",
    "shavers": "grooming",
    "hair dryers": "grooming",
    "hair straighteners": "grooming",
    "electric toothbrushes": "grooming",
    # Gaming
    "gaming consoles": "gaming",
    "gaming accessories": "gaming",
    "gaming headsets": "audio",
}

# ---------------------------------------------------------------------------
# Seed category URLs — Croma uses category IDs in URLs
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 20  # pages for top categories
_STD = 10  # pages for standard categories

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones ─────────────────────────────────────────────────────
    ("https://www.croma.com/phones-wearables/mobile-phones/c/22", _TOP),
    ("https://www.croma.com/phones-wearables/mobile-accessories/c/23", _STD),
    # ── Laptops & Computers ─────────────────────────────────────────────
    ("https://www.croma.com/computers-tablets/laptops/c/30", _TOP),
    ("https://www.croma.com/computers-tablets/tablets/c/31", _STD),
    ("https://www.croma.com/computers-tablets/monitors/c/474", _STD),
    ("https://www.croma.com/computers-tablets/printers-scanners/c/35", _STD),
    ("https://www.croma.com/computers-tablets/networking/c/33", _STD),
    ("https://www.croma.com/computers-tablets/storage-devices/c/34", _STD),
    # ── TVs ─────────────────────────────────────────────────────────────
    ("https://www.croma.com/televisions-accessories/led-tvs/c/392", _TOP),
    ("https://www.croma.com/televisions-accessories/projectors/c/14", _STD),
    ("https://www.croma.com/televisions-accessories/streaming-devices/c/395", _STD),
    # ── Audio ───────────────────────────────────────────────────────────
    ("https://www.croma.com/audio-video/headphones-earphones/c/17", _TOP),
    ("https://www.croma.com/audio-video/bluetooth-portable-speakers/c/459", _TOP),
    ("https://www.croma.com/audio-video/soundbars-home-theatre/c/16", _STD),
    ("https://www.croma.com/audio-video/party-speakers/c/461", _STD),
    # ── Wearables ───────────────────────────────────────────────────────
    ("https://www.croma.com/phones-wearables/smart-watches-bands/c/463", _TOP),
    # ── Cameras ─────────────────────────────────────────────────────────
    ("https://www.croma.com/cameras-accessories/digital-cameras/c/36", _STD),
    ("https://www.croma.com/cameras-accessories/action-cameras/c/40", _STD),
    # ── Large Appliances ────────────────────────────────────────────────
    ("https://www.croma.com/home-appliances/refrigerators/c/5", _TOP),
    ("https://www.croma.com/home-appliances/washing-machines/c/7", _TOP),
    ("https://www.croma.com/home-appliances/air-conditioners/c/3", _TOP),
    ("https://www.croma.com/home-appliances/microwave-ovens/c/475", _STD),
    ("https://www.croma.com/home-appliances/dishwashers/c/472", _STD),
    ("https://www.croma.com/home-appliances/water-heaters/c/476", _STD),
    # ── Small Appliances ────────────────────────────────────────────────
    ("https://www.croma.com/home-appliances/air-purifiers/c/430", _STD),
    ("https://www.croma.com/home-appliances/water-purifiers/c/470", _STD),
    ("https://www.croma.com/home-appliances/vacuum-cleaners/c/471", _STD),
    ("https://www.croma.com/home-appliances/fans/c/477", _STD),
    # ── Kitchen Appliances ──────────────────────────────────────────────
    ("https://www.croma.com/kitchen-appliances/mixer-grinders-juicers/c/46", _STD),
    ("https://www.croma.com/kitchen-appliances/air-fryer/c/487", _STD),
    ("https://www.croma.com/kitchen-appliances/coffee-machines/c/51", _STD),
    ("https://www.croma.com/kitchen-appliances/induction-cooktops/c/489", _STD),
    ("https://www.croma.com/kitchen-appliances/electric-kettles/c/488", _STD),
    ("https://www.croma.com/kitchen-appliances/oven-toaster-grills/c/48", _STD),
    ("https://www.croma.com/kitchen-appliances/gas-stoves-hobs/c/490", _STD),
    # ── Personal Care ───────────────────────────────────────────────────
    ("https://www.croma.com/personal-care/trimmers-shavers/c/62", _STD),
    ("https://www.croma.com/personal-care/hair-care/c/479", _STD),
    # ── Gaming ──────────────────────────────────────────────────────────
    ("https://www.croma.com/gaming/gaming-consoles/c/458", _STD),
    ("https://www.croma.com/gaming/gaming-accessories/c/482", _STD),
]

MAX_LISTING_PAGES = 5


class CromaSpider(BaseWhydudSpider):
    """Scrapes Croma.com electronics store.

    Croma embeds product data in window.__INITIAL_DATA__ as JSON:
    - plpReducer: product listing data on category/search pages
    - pdpReducer: full product detail data on product pages

    This allows HTTP-only scraping (no Playwright) for most pages.
    Playwright is used as fallback when __INITIAL_DATA__ is incomplete.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "croma"
    allowed_domains = ["croma.com", "www.croma.com"]

    QUICK_MODE_CATEGORIES = 8

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
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
            f"Croma spider finished ({reason}): "
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
    # start_requests — HTTP for category listing pages
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit HTTP requests for all category listing pages."""
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("?page=")[0].split("&page=")[0]
            self._max_pages_map[base] = max_pg

            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={"category_slug": self._resolve_category_from_url(url)},
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (HTTP)")

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

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path."""
        # Try to match URL path segments against our category map
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword.replace(" ", "-") in path:
                return slug
        return None

    def _extract_initial_data(self, response) -> dict | None:
        """Extract window.__INITIAL_DATA__ JSON from page source."""
        # Match: window.__INITIAL_DATA__ = {...};
        match = re.search(
            r"window\.__INITIAL_DATA__\s*=\s*(\{.+?\})\s*;?\s*</script>",
            response.text,
            re.DOTALL,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"Failed to parse __INITIAL_DATA__ on {response.url}")
            return None

    def _parse_price(self, price_str: str | None) -> Decimal | None:
        """Parse price string to Decimal in paisa."""
        if not price_str:
            return None
        match = PRICE_RE.search(str(price_str))
        if not match:
            return None
        try:
            rupees = Decimal(match.group().replace(",", ""))
            return rupees * 100  # convert to paisa
        except (InvalidOperation, ValueError):
            return None

    def _is_blocked(self, response) -> bool:
        """Detect if Croma served a block/error page."""
        if response.status in (403, 429):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages (category / search results)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from category listing page.

        Strategy:
        1. Parse window.__INITIAL_DATA__ → plpReducer for product data
        2. Fallback: parse HTML product cards
        3. Promote to Playwright if both fail
        """
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            if not response.meta.get("playwright"):
                self.logger.info(f"Blocked on listing {response.url} (HTTP) — promoting to Playwright")
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "networkidle"),
                            PageMethod("wait_for_timeout", 3000),
                        ],
                        "category_slug": response.meta.get("category_slug"),
                    },
                    dont_filter=True,
                )
            else:
                self.logger.warning(f"Blocked on listing {response.url} even with Playwright — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: Extract from __INITIAL_DATA__
        data = self._extract_initial_data(response)
        products = []
        if data:
            plp = data.get("plpReducer") or data.get("searchReducer") or {}
            product_list = plp.get("products") or plp.get("searchProducts") or []
            if isinstance(product_list, list):
                products = product_list

        if products:
            self.logger.info(f"Found {len(products)} products (JSON) on {response.url}")
            for prod in products:
                prod_url = prod.get("url", "")
                if not prod_url:
                    continue
                full_url = response.urljoin(prod_url)

                # Yield detail page request (HTTP first, Playwright fallback in parse_product)
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={"category_slug": category_slug},
                )
        else:
            # Strategy 2: Parse HTML product cards
            cards = response.css("li.product-item, div.product-card, a[href*='/p/']")
            if cards:
                self.logger.info(f"Found {len(cards)} products (HTML) on {response.url}")
                for card in cards:
                    href = card.css("a::attr(href)").get() or card.attrib.get("href", "")
                    if "/p/" in href:
                        full_url = response.urljoin(href)
                        yield scrapy.Request(
                            full_url,
                            callback=self.parse_product_page,
                            errback=self.handle_error,
                            headers=self._make_headers(),
                            meta={"category_slug": category_slug},
                        )
            else:
                # Strategy 3: Promote to Playwright
                if not response.meta.get("playwright"):
                    self.logger.info(f"No products found via HTTP on {response.url} — trying Playwright")
                    yield scrapy.Request(
                        response.url,
                        callback=self.parse_listing_page,
                        errback=self.handle_error,
                        headers=self._make_headers(),
                        meta={
                            "playwright": True,
                            "playwright_page_init_callback": self._apply_stealth,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "networkidle"),
                                PageMethod("wait_for_timeout", 3000),
                            ],
                            "category_slug": category_slug,
                        },
                        dont_filter=True,
                    )
                else:
                    self.logger.warning(f"No products found on {response.url} even with Playwright")
                return

        # Pagination
        base_url = response.url.split("?page=")[0].split("&page=")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            # Croma uses ?page=N (0-indexed)
            next_page = pages_so_far
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page={next_page}"
            self._pages_followed[base_url] = pages_so_far + 1
            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={"category_slug": category_slug},
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page.

        Strategy:
        1. Parse window.__INITIAL_DATA__ → pdpReducer
        2. Fallback: JSON-LD structured data
        3. Fallback: CSS/XPath extraction
        4. Promote to Playwright if all fail
        """
        if self._is_blocked(response):
            if not response.meta.get("playwright"):
                self.logger.info(f"Blocked on product {response.url} (HTTP) — promoting to Playwright")
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "domcontentloaded"),
                            PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                        ],
                        "category_slug": response.meta.get("category_slug"),
                    },
                    dont_filter=True,
                )
            else:
                self.logger.warning(f"Blocked on product {response.url} even with Playwright")
                self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")

        # Extract product code from URL
        code_match = PRODUCT_CODE_RE.search(response.url)
        external_id = code_match.group(1) if code_match else None

        # Strategy 1: __INITIAL_DATA__ → pdpReducer
        data = self._extract_initial_data(response)
        if data and "pdpReducer" in data:
            item = self._parse_from_pdp_reducer(data["pdpReducer"], response.url, category_slug, external_id)
            if item:
                self._product_pages_scraped += 1
                self._products_extracted += 1
                self.items_scraped += 1
                yield item
                return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug, external_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: CSS/XPath extraction
        item = self._parse_from_html(response, category_slug, external_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 4: Playwright fallback
        if not response.meta.get("playwright"):
            self.logger.info(f"HTTP extraction failed for {response.url} — trying Playwright")
            yield scrapy.Request(
                response.url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                    ],
                    "category_slug": category_slug,
                },
                dont_filter=True,
            )
        else:
            self.logger.warning(f"Could not extract product data from {response.url}")
            self.items_failed += 1

    # ------------------------------------------------------------------
    # Extraction: pdpReducer (primary)
    # ------------------------------------------------------------------

    def _parse_from_pdp_reducer(
        self, pdp: dict, url: str, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from Croma's pdpReducer JSON."""
        product = pdp.get("productDetails") or pdp
        name = product.get("name") or product.get("productName")
        if not name or name == "undefined":
            return None

        code = external_id or str(product.get("code", ""))
        if not code:
            return None

        # Price extraction
        selling_price = self._parse_price(product.get("sellingPrice") or product.get("price", {}).get("value"))
        mrp = self._parse_price(product.get("mrp") or product.get("oldPrice", {}).get("value"))

        # Images
        images = []
        for img in product.get("images") or product.get("galleryImages") or []:
            img_url = img.get("url") or img.get("zoomImageUrl") or img.get("imageUrl") or ""
            if img_url:
                if img_url.startswith("//"):
                    img_url = "https:" + img_url
                elif img_url.startswith("/"):
                    img_url = "https://www.croma.com" + img_url
                images.append(img_url)

        # Specs
        specs = {}
        for spec_group in product.get("classifications") or product.get("specifications") or []:
            for feature in spec_group.get("features") or []:
                key = feature.get("name", "")
                val = feature.get("featureValues", [{}])[0].get("value", "") if feature.get("featureValues") else ""
                if not val:
                    val = feature.get("value", "")
                if key and val:
                    specs[key] = val

        # Brand
        brand = product.get("brandName") or product.get("brand") or specs.get("Brand")

        # Rating
        rating = None
        review_count = None
        rating_val = product.get("finalReviewRating") or product.get("averageOverallRating")
        if rating_val and str(rating_val) not in ("0", "0.0", ""):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = product.get("finalReviewRatingCount") or product.get("numberOfReviews")
        if count_val and str(count_val) not in ("0", ""):
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = product.get("availableForPickup", True) or product.get("inStock", True)
        stock_info = product.get("stockInfo") or {}
        if stock_info.get("stockLevelStatus") == "outOfStock":
            in_stock = False

        # Warranty
        warranty = product.get("warrantyText") or None
        if not warranty:
            std = product.get("standardWarranty")
            if std:
                warranty = f"{std} months"

        # Delivery
        delivery_info = product.get("deliveryDate") or product.get("estimatedDelivery")

        # Category from keyword map or meta
        if not category_slug:
            cats = product.get("categoryNames") or []
            for cat_name in cats:
                cat_lower = cat_name.lower()
                for kw, slug in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_lower:
                        category_slug = slug
                        break
                if category_slug:
                    break

        # Breadcrumbs
        breadcrumbs = []
        for bc in product.get("breadCrumbs") or []:
            name_bc = bc.get("name") or bc.get("categoryName")
            if name_bc:
                breadcrumbs.append(name_bc)

        # Description
        description = product.get("description") or product.get("summary")

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=code,
            url=f"https://www.croma.com/p/{code}" if "/p/" not in url else url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name="Croma",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="Croma",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=warranty,
            delivery_info=delivery_info,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=specs.get("Country of Origin"),
            manufacturer=specs.get("Manufacturer") or specs.get("Brand"),
            model_number=specs.get("Model Number") or specs.get("Model Name"),
            weight=specs.get("Weight") or specs.get("Product Weight"),
            dimensions=specs.get("Dimensions") or specs.get("Product Dimensions"),
        )

    # ------------------------------------------------------------------
    # Extraction: JSON-LD (secondary)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self, response, category_slug: str | None, external_id: str | None,
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
            if not name or name == "undefined":
                continue

            sku = ld_data.get("sku") or external_id
            if not sku or sku == "undefined":
                continue

            offers = ld_data.get("offers") or {}
            price = self._parse_price(offers.get("price"))
            brand_data = ld_data.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data)

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
            if agg_rating.get("reviewCount"):
                try:
                    review_count = int(agg_rating["reviewCount"])
                except (ValueError, TypeError):
                    pass

            in_stock = True
            availability = offers.get("availability", "")
            if "OutOfStock" in availability:
                in_stock = False

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url,
                title=name,
                brand=brand if brand else None,
                price=price,
                mrp=None,
                images=images,
                rating=rating,
                review_count=review_count,
                specs={},
                seller_name="Croma",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="Croma",
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

    # ------------------------------------------------------------------
    # Extraction: HTML/CSS fallback
    # ------------------------------------------------------------------

    def _parse_from_html(
        self, response, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from HTML as last resort."""
        title = response.css("h1.pd-title::text, h1.product-title::text, h1::text").get()
        if not title:
            return None
        title = title.strip()

        code = external_id
        if not code:
            code_match = PRODUCT_CODE_RE.search(response.url)
            code = code_match.group(1) if code_match else None
        if not code:
            return None

        price_text = response.css(
            "span.pdp-selling-price::text, span.new-price::text, "
            "span.amount::text, div.selling-price span::text"
        ).get()
        price = self._parse_price(price_text)

        mrp_text = response.css(
            "span.pdp-mrp-price::text, span.old-price::text, "
            "span.list-price::text"
        ).get()
        mrp = self._parse_price(mrp_text)

        brand = response.css("span.brand-name::text, div.brand-name::text").get()

        images = response.css(
            "img.pdp-image::attr(src), div.product-gallery img::attr(src), "
            "img.product-image::attr(src)"
        ).getall()
        images = [img for img in images if img and not img.startswith("data:")]

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=code,
            url=response.url,
            title=title,
            brand=brand.strip() if brand else None,
            price=price,
            mrp=mrp,
            images=images,
            rating=None,
            review_count=None,
            specs={},
            seller_name="Croma",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Croma",
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
            manufacturer=None,
            model_number=None,
            weight=None,
            dimensions=None,
        )
