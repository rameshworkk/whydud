"""Myntra spider — camoufox-based scraper for PerimeterX bypass.

Architecture:
  Myntra (Flipkart Group) is a React SPA protected by PerimeterX / HUMAN
  anti-bot.  Playwright (even with stealth) is blocked.  Only camoufox
  (anti-detection Firefox) passes reliably.

  Strategy:
    1. Category-based discovery: /{category}?p={page} via camoufox
       → extract product URLs from DOM product cards or window.__myx state.
    2. Product detail pages: camoufox renders PDP → try embedded JSON
       first (pdpData / window.__myx), fall back to JSON-LD, then DOM
       parsing with Myntra-specific CSS selectors.

  Anti-bot: PerimeterX (Flipkart Group — aggressive, blocks Playwright)
  All prices in RUPEES — converted to paisa (* 100) before yielding.

URL patterns:
  Category: /men-tshirts?p={page}  → ~50 products per page
  Product:  /brand/product-name/{numeric_id}
"""

from __future__ import annotations

import json
import logging
import re
import threading
from decimal import Decimal, InvalidOperation

import scrapy
from scrapy import signals
from scrapy.http import HtmlResponse

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PRODUCT_ID_RE = re.compile(r"/(\d{5,})(?:\?|$)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")
RATING_NUM_RE = re.compile(r"([\d.]+)")

MARKETPLACE_SLUG = "myntra"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Men
    "men-tshirts": "mens-fashion",
    "men-shirts": "mens-fashion",
    "men-jeans": "mens-fashion",
    "men-trousers": "mens-fashion",
    "men-shorts": "mens-fashion",
    "men-jackets": "mens-fashion",
    "men-sweaters": "mens-fashion",
    "men-kurtas": "mens-fashion",
    "men-track-pants": "mens-fashion",
    "men-innerwear": "mens-fashion",
    # Women
    "women-kurtas-kurtis": "womens-fashion",
    "women-tops": "womens-fashion",
    "women-dresses": "womens-fashion",
    "women-jeans": "womens-fashion",
    "women-sarees": "womens-fashion",
    "women-leggings": "womens-fashion",
    "women-ethnic-wear": "womens-fashion",
    "women-western-wear": "womens-fashion",
    "women-nightwear": "womens-fashion",
    # Kids
    "kids-clothing": "kids-fashion",
    "boys-clothing": "kids-fashion",
    "girls-clothing": "kids-fashion",
    # Footwear
    "men-casual-shoes": "footwear",
    "men-sports-shoes": "footwear",
    "men-formal-shoes": "footwear",
    "men-sandals": "footwear",
    "women-flats": "footwear",
    "women-heels": "footwear",
    "women-sneakers": "footwear",
    "sports-shoes": "footwear",
    # Accessories
    "men-watches": "watches",
    "women-watches": "watches",
    "sunglasses": "accessories",
    "bags-backpacks": "accessories",
    "belts": "accessories",
    "wallets": "accessories",
    "jewellery": "jewellery",
    # Beauty
    "lipstick": "makeup",
    "foundation": "makeup",
    "nail-polish": "makeup",
    "makeup": "makeup",
    "skincare": "skincare",
    "haircare": "hair-care",
    "fragrance": "fragrance",
    "bath-body": "bath-body",
}

# ---------------------------------------------------------------------------
# Seed URLs — (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # Men
    ("https://www.myntra.com/men-tshirts", _TOP),
    ("https://www.myntra.com/men-shirts", _STD),
    ("https://www.myntra.com/men-jeans", _STD),
    ("https://www.myntra.com/men-trousers", _STD),
    ("https://www.myntra.com/men-jackets", _STD),
    ("https://www.myntra.com/men-kurtas", _STD),
    # Women
    ("https://www.myntra.com/women-kurtas-kurtis-suits", _TOP),
    ("https://www.myntra.com/women-tops-t-shirts", _STD),
    ("https://www.myntra.com/women-dresses", _STD),
    ("https://www.myntra.com/women-sarees", _STD),
    ("https://www.myntra.com/women-jeans", _STD),
    # Kids
    ("https://www.myntra.com/kids-clothing", _STD),
    # Footwear
    ("https://www.myntra.com/men-casual-shoes", _TOP),
    ("https://www.myntra.com/men-sports-shoes", _STD),
    ("https://www.myntra.com/women-flats", _STD),
    ("https://www.myntra.com/women-heels", _STD),
    ("https://www.myntra.com/sports-shoes", _STD),
    # Watches & Accessories
    ("https://www.myntra.com/men-watches", _STD),
    ("https://www.myntra.com/women-watches", _STD),
    ("https://www.myntra.com/sunglasses", _STD),
    ("https://www.myntra.com/bags-backpacks", _STD),
    # Beauty
    ("https://www.myntra.com/lipstick", _STD),
    ("https://www.myntra.com/foundation", _STD),
    ("https://www.myntra.com/skincare", _STD),
    ("https://www.myntra.com/haircare", _STD),
    ("https://www.myntra.com/fragrance-for-men", _STD),
]

MAX_LISTING_PAGES = 5
QUICK_MODE_CATEGORIES = 5


# ---------------------------------------------------------------------------
# Camoufox downloader middleware
# ---------------------------------------------------------------------------


class MyntraCamoufoxMiddleware:
    """Scrapy downloader middleware using camoufox (anti-detection Firefox).

    Camoufox bypasses PerimeterX / HUMAN anti-bot which blocks Playwright,
    curl_cffi, and even headed Chrome with stealth patches.  It achieves
    this by using a patched Firefox binary with realistic fingerprints.

    Runs camoufox sync API in a dedicated thread (via asyncio.run_in_executor)
    because:
      - Sync API can't run in Scrapy's asyncio event loop (detects it)
      - Async API needs ProactorEventLoop on Windows (Scrapy uses Selector)

    The middleware manages a single browser context that persists across
    requests for cookie/session continuity.  A threading lock serialises
    page operations to avoid greenlet cross-thread errors.
    """

    def __init__(self) -> None:
        self._context = None
        self._camoufox_cm = None
        self._request_count = 0
        self._lock = threading.Lock()

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def _ensure_browser(self):
        """Start camoufox browser (called in worker thread)."""
        if self._context is not None:
            return

        import asyncio
        import sys

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from camoufox.sync_api import Camoufox

        self._camoufox_cm = Camoufox(headless=True)
        self._context = self._camoufox_cm.__enter__()
        logger.info("Camoufox browser started for Myntra spider (thread pool)")

    def _fetch_page(self, url: str, wait_ms: int) -> tuple[int, bytes]:
        """Render a page with camoufox (runs in worker thread).

        A threading lock serialises all page operations so camoufox's
        internal greenlet never sees cross-thread switches.
        """
        with self._lock:
            self._ensure_browser()
            page = self._context.new_page()
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
                status = resp.status if resp else 200
                page.wait_for_timeout(wait_ms)
                content = page.content()
                return status, content.encode("utf-8")
            finally:
                page.close()

    async def process_request(self, request, spider):
        """Intercept requests to myntra.com and render via camoufox."""
        if request.meta.get("skip_camoufox"):
            return None
        if "myntra.com" not in request.url:
            return None

        self._request_count += 1
        wait_ms = request.meta.get("camoufox_wait_ms", 10000)

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            status, body = await loop.run_in_executor(
                None, self._fetch_page, request.url, wait_ms
            )

            return HtmlResponse(
                url=request.url,
                status=status,
                body=body,
                request=request,
                encoding="utf-8",
            )

        except Exception as exc:
            logger.warning(f"Camoufox request failed for {request.url}: {exc}")
            return HtmlResponse(
                url=request.url,
                status=503,
                body=b"",
                request=request,
                encoding="utf-8",
            )

    def spider_closed(self, spider):
        """Shut down camoufox browser."""
        if self._context is not None:
            try:
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    pool.submit(self._camoufox_cm.__exit__, None, None, None).result(
                        timeout=15
                    )
            except Exception as exc:
                logger.warning(f"Error closing camoufox: {exc}")
            self._context = None
            self._camoufox_cm = None
        logger.info(
            f"Camoufox middleware closed — {self._request_count} requests served"
        )


# ---------------------------------------------------------------------------
# Spider
# ---------------------------------------------------------------------------


class MyntraSpider(BaseWhydudSpider):
    """Scrapes Myntra.com — fashion marketplace with aggressive PerimeterX.

    Uses camoufox (anti-detection Firefox) instead of Playwright.
    Two-phase: category pages for discovery → product pages for detail.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override category URLs.
      urls          — comma-separated direct product URLs.
      max_pages     — max listing pages per category (default 5).
    """

    name = "myntra"
    allowed_domains = ["myntra.com", "www.myntra.com"]

    QUICK_MODE_CATEGORIES = 5

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 1,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 410, 429, 503],
        # Disable Playwright — we use camoufox middleware instead.
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
            "http": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
        },
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.spiders.myntra_spider.MyntraCamoufoxMiddleware": 100,
            "apps.scraping.middlewares.BackoffRetryMiddleware": 350,
        },
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        job_id: str | None = None,
        category_urls: str | None = None,
        urls: str | None = None,
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
        self._override_urls: list[str] = (
            [u.strip() for u in urls.split(",") if u.strip()] if urls else []
        )
        self._max_pages_override: int | None = int(max_pages) if max_pages else None
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._blocked_count: int = 0
        self._state_extractions: int = 0
        self._json_ld_extractions: int = 0
        self._dom_extractions: int = 0
        self._listing_data_extractions: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Myntra spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"blocked={self._blocked_count}, "
            f"state={self._state_extractions}, json_ld={self._json_ld_extractions}, "
            f"dom={self._dom_extractions}, listing={self._listing_data_extractions}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit requests for Myntra category or product pages."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob

                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        # Direct product URLs
        if self._override_urls:
            for url in self._override_urls:
                yield scrapy.Request(
                    url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    meta={
                        "category_slug": self._resolve_category_from_url(url),
                        "camoufox_wait_ms": 10000,
                    },
                    dont_filter=True,
                )
            self.logger.info(
                f"Queued {len(self._override_urls)} direct product URLs (camoufox)"
            )
            return

        # Direct category URLs
        if self._category_urls:
            fallback = self._max_pages_override or MAX_LISTING_PAGES
            for url in self._category_urls:
                if "/p/" in url or PRODUCT_ID_RE.search(url):
                    # Looks like a product URL
                    yield scrapy.Request(
                        url,
                        callback=self.parse_product_page,
                        errback=self.handle_error,
                        meta={
                            "category_slug": self._resolve_category_from_url(url),
                            "camoufox_wait_ms": 10000,
                        },
                        dont_filter=True,
                    )
                else:
                    base = url.split("?")[0]
                    self._max_pages_map[base] = fallback
                    yield scrapy.Request(
                        url,
                        callback=self.parse_listing_page,
                        errback=self.handle_error,
                        meta={
                            "category_slug": self._resolve_category_from_url(url),
                            "camoufox_wait_ms": 12000,
                        },
                        dont_filter=True,
                    )
            self.logger.info(
                f"Queued {len(self._category_urls)} category URLs (camoufox)"
            )
            return

        # Default: seed categories
        url_pairs = self._load_urls()
        for url, max_pg in url_pairs:
            base = url.split("?")[0]
            self._max_pages_map[base] = max_pg
            self.logger.info(f"Queuing Myntra category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                meta={
                    "category_slug": self._resolve_category_from_url(url),
                    "camoufox_wait_ms": 12000,
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} Myntra categories (camoufox)")

    def _load_urls(self) -> list[tuple[str, int]]:
        """Resolve the list of (url, max_pages) to crawl."""
        fallback = self._max_pages_override or MAX_LISTING_PAGES
        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[: self.QUICK_MODE_CATEGORIES]
                ]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from a Myntra category listing page."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self._blocked_count += 1
            self.logger.warning(
                f"Blocked on listing {response.url} (HTTP {response.status})"
            )
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: window.__myx state — richest source
        state = self._extract_myx_state(response)
        products = []
        if state:
            for key in ("searchData", "products", "results", "productList"):
                section = state.get(key) or {}
                prod_list = (
                    section.get("results")
                    or section.get("products")
                    or section.get("items")
                    or []
                )
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(
                f"Found {len(products)} products (__myx state) on {response.url}"
            )
            for prod in products:
                prod_id = prod.get("productId") or prod.get("id")
                slug = prod.get("landingPageUrl") or prod.get("url") or ""
                if not prod_id:
                    continue
                if slug.startswith("/"):
                    product_url = f"https://www.myntra.com{slug}"
                else:
                    product_url = f"https://www.myntra.com/{prod_id}"

                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    meta={
                        "category_slug": category_slug,
                        "listing_data": prod,
                        "camoufox_wait_ms": 10000,
                    },
                    dont_filter=True,
                )
        else:
            # Strategy 2: Extract product links from DOM
            links: set[str] = set()
            for sel in [
                "li.product-base a::attr(href)",
                "a[href*='/buy/']::attr(href)",
                "a[data-refreshpage]::attr(href)",
                '.product-base a[href*="/"]::attr(href)',
            ]:
                for href in response.css(sel).getall():
                    full = response.urljoin(href)
                    if re.search(r"/\d{5,}", full):
                        links.add(full.split("?")[0])

            # Regex fallback for product links in page source
            if not links:
                for match in re.finditer(
                    r'href="(/[^"]*?/(\d{6,}))"', response.text
                ):
                    href = match.group(1)
                    full = f"https://www.myntra.com{href}"
                    links.add(full.split("?")[0])

            if links:
                self.logger.info(
                    f"Found {len(links)} products (DOM) on {response.url}"
                )
                for prod_url in links:
                    yield scrapy.Request(
                        prod_url,
                        callback=self.parse_product_page,
                        errback=self.handle_error,
                        meta={
                            "category_slug": category_slug,
                            "camoufox_wait_ms": 10000,
                        },
                        dont_filter=True,
                    )
            else:
                self.logger.warning(f"No products found on {response.url}")
                return

        # Pagination — Myntra uses ?p={page_number}
        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            next_url = f"{base_url}?p={next_page}&sort=popularity"
            self._pages_followed[base_url] = next_page

            self.logger.info(
                f"Following page {next_page}/{max_for_category}: {next_url}"
            )
            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                meta={
                    "category_slug": category_slug,
                    "camoufox_wait_ms": 12000,
                },
                dont_filter=True,
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from a Myntra product detail page."""
        if self._is_blocked(response):
            self._blocked_count += 1
            self.logger.warning(
                f"Blocked on product {response.url} (HTTP {response.status})"
            )
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        id_match = PRODUCT_ID_RE.search(response.url)
        external_id = id_match.group(1) if id_match else None

        # Strategy 1: window.__myx state (richest source)
        state = self._extract_myx_state(response)
        if state:
            pdp = (
                state.get("pdpData")
                or state.get("productData")
                or state.get("product")
                or {}
            )
            if pdp.get("name") or pdp.get("productName"):
                item = self._build_from_state(
                    pdp, response.url, category_slug, external_id
                )
                if item:
                    self._state_extractions += 1
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD structured data
        item = self._build_from_json_ld(response, category_slug, external_id)
        if item:
            self._json_ld_extractions += 1
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: DOM parsing
        item = self._build_from_dom(response, category_slug, external_id)
        if item:
            self._dom_extractions += 1
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 4: Listing data fallback (less detail but usable)
        if listing_data:
            item = self._build_from_listing(
                listing_data, response.url, category_slug, external_id
            )
            if item:
                self._listing_data_extractions += 1
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # State extraction
    # ------------------------------------------------------------------

    def _extract_myx_state(self, response) -> dict | None:
        """Extract window.__myx React app state from rendered page."""
        # CSS selector approach
        for script_text in response.css("script::text").getall():
            if "window.__myx" not in script_text:
                continue
            match = re.search(
                r"window\.__myx\s*=\s*(\{.+?\})\s*;?\s*(?:</script>|$)",
                script_text,
                re.DOTALL,
            )
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, ValueError):
                    pass

        # Regex fallback on full page source
        match = re.search(
            r"window\.__myx\s*=\s*(\{.+?\})\s*;?\s*</script>",
            response.text,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass

        # Also try pdpData = {...} pattern
        match = re.search(
            r"pdpData\s*=\s*(\{.+?\})\s*;",
            response.text,
            re.DOTALL,
        )
        if match:
            try:
                data = json.loads(match.group(1))
                return {"pdpData": data}
            except (json.JSONDecodeError, ValueError):
                pass

        return None

    # ------------------------------------------------------------------
    # Item builders
    # ------------------------------------------------------------------

    def _build_from_state(
        self,
        pdp: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from window.__myx product state."""
        name = pdp.get("name") or pdp.get("productName")
        if not name:
            return None
        name = str(name).strip()

        pid = external_id or str(pdp.get("id") or pdp.get("productId") or "")
        if not pid:
            return None

        # Prices — in rupees, convert to paisa
        selling_price = self._parse_price(
            pdp.get("discountedPrice") or pdp.get("price")
        )
        mrp = self._parse_price(pdp.get("mrp"))

        # Check nested price object
        if selling_price is None:
            price_obj = pdp.get("price")
            if isinstance(price_obj, dict):
                selling_price = self._parse_price(
                    price_obj.get("discounted") or price_obj.get("value")
                )

        # Check sizes array for price (some structures nest it there)
        if selling_price is None and isinstance(pdp.get("sizes"), list):
            for size in pdp["sizes"]:
                if isinstance(size, dict):
                    selling_price = self._parse_price(size.get("discountedPrice"))
                    if mrp is None:
                        mrp = self._parse_price(size.get("mrp"))
                    if selling_price:
                        break

        # Brand
        brand = pdp.get("brand") or pdp.get("brandName")
        if isinstance(brand, dict):
            brand = brand.get("name")
        brand = str(brand).strip() if brand else None

        # Images
        images = self._extract_state_images(pdp)

        # Rating / reviews
        rating, review_count = self._extract_state_rating(pdp)

        # Description
        description = pdp.get("productDescription") or pdp.get("description")

        # Specs from articleAttributes or productDetails
        specs = {}
        for key, val in (pdp.get("articleAttributes") or {}).items():
            if key and val:
                specs[str(key).strip()] = str(val).strip()

        for detail in pdp.get("productDetails") or []:
            if isinstance(detail, dict):
                k = detail.get("title") or detail.get("key")
                v = detail.get("description") or detail.get("value")
                if k and v:
                    specs[str(k).strip()] = str(v).strip()

        # Sizes
        sizes = self._extract_state_sizes(pdp)
        if sizes:
            specs["sizes_available"] = ", ".join(sizes)

        # Size & fit description
        size_fit = pdp.get("sizeFitDesc") or pdp.get("sizeAndFit")
        if isinstance(size_fit, str) and size_fit.strip():
            specs["Size & Fit"] = size_fit.strip()

        # Breadcrumbs
        breadcrumbs = []
        for crumb in pdp.get("breadcrumbs") or pdp.get("breadCrumb") or []:
            if isinstance(crumb, dict):
                name_val = crumb.get("name") or crumb.get("displayName")
                if name_val:
                    breadcrumbs.append(str(name_val))
            elif isinstance(crumb, str):
                breadcrumbs.append(crumb)

        # Variants (colours)
        variants = []
        for color in pdp.get("colours") or pdp.get("colors") or []:
            if isinstance(color, dict):
                c_name = color.get("name") or color.get("label")
                if c_name:
                    v: dict = {"type": "color", "value": str(c_name).strip()}
                    c_url = color.get("url") or color.get("landingPageUrl")
                    if c_url:
                        v["url"] = c_url
                    variants.append(v)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url.split("?")[0],
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=[img for img in images if img],
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name="Myntra",
            seller_rating=None,
            in_stock=pdp.get("inStock", True),
            fulfilled_by="Myntra",
            category_slug=category_slug or self._resolve_category_from_url(url),
            about_bullets=[],
            offer_details=self._extract_state_offers(pdp),
            raw_html_path=None,
            description=description,
            warranty=None,
            delivery_info=self._extract_state_delivery(pdp),
            return_policy=pdp.get("returnPolicy"),
            breadcrumbs=breadcrumbs,
            variant_options=variants,
            country_of_origin=self._find_spec(
                specs, ["Country of Origin", "country of origin"]
            ),
            manufacturer=self._find_spec(specs, ["Manufacturer", "manufacturer"]) or brand,
            model_number=self._find_spec(
                specs, ["Article Number", "Style Code", "Model Number"]
            ),
            weight=self._find_spec(specs, ["Weight", "Net Weight"]),
            dimensions=self._find_spec(specs, ["Dimensions"]),
        )

    @staticmethod
    def _extract_state_images(pdp: dict) -> list[str]:
        """Extract images from __myx product state."""
        images: list[str] = []

        # Pattern 1: media.images
        media = pdp.get("media")
        if isinstance(media, dict):
            for img in media.get("images") or []:
                if isinstance(img, dict):
                    src = img.get("src") or img.get("url") or img.get("secureSrc")
                    if src:
                        images.append(src)
                elif isinstance(img, str):
                    images.append(img)

        # Pattern 2: images or imageUrls
        if not images:
            for img in pdp.get("images") or pdp.get("imageUrls") or []:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, dict):
                    src = img.get("src") or img.get("url")
                    if src:
                        images.append(src)

        # Pattern 3: searchImage (from listing data in state)
        if not images:
            search_img = pdp.get("searchImage")
            if isinstance(search_img, str):
                images.append(search_img)

        # Deduplicate
        seen: set[str] = set()
        deduped: list[str] = []
        for img in images:
            if img and img not in seen:
                seen.add(img)
                deduped.append(img)
        return deduped

    @staticmethod
    def _extract_state_rating(pdp: dict) -> tuple[Decimal | None, int | None]:
        """Extract rating and review count from state."""
        rating = None
        review_count = None

        ratings = pdp.get("ratings") or pdp.get("rating") or {}
        if isinstance(ratings, dict):
            rv = ratings.get("averageRating") or ratings.get("ratingValue")
            if rv is not None:
                try:
                    rating = Decimal(str(rv))
                except (InvalidOperation, ValueError):
                    pass
            rc = ratings.get("totalCount") or ratings.get("ratingCount") or ratings.get("reviewCount")
            if rc is not None:
                try:
                    review_count = int(rc)
                except (ValueError, TypeError):
                    pass

        # Direct fields fallback
        if rating is None:
            rv = pdp.get("averageRating") or pdp.get("overallRating")
            if rv is not None:
                try:
                    rating = Decimal(str(rv))
                except (InvalidOperation, ValueError):
                    pass

        if review_count is None:
            rc = pdp.get("reviewCount") or pdp.get("ratingCount")
            if rc is not None:
                try:
                    review_count = int(rc)
                except (ValueError, TypeError):
                    pass

        return rating, review_count

    @staticmethod
    def _extract_state_sizes(pdp: dict) -> list[str]:
        """Extract available sizes from state."""
        sizes: list[str] = []
        for size in pdp.get("sizes") or []:
            if isinstance(size, dict):
                label = size.get("label") or size.get("sizeValue") or size.get("size")
                # Only include available sizes
                if label and size.get("available", True):
                    sizes.append(str(label))
            elif isinstance(size, str):
                sizes.append(size)
        return list(dict.fromkeys(sizes))

    @staticmethod
    def _extract_state_offers(pdp: dict) -> list[dict]:
        """Extract offers/promotions from state."""
        offers: list[dict] = []
        for offer in pdp.get("offers") or pdp.get("promotions") or []:
            if isinstance(offer, dict):
                text = (
                    offer.get("title")
                    or offer.get("description")
                    or offer.get("text")
                )
                if text:
                    offers.append({"type": "offer", "text": str(text).strip()})
        return offers

    @staticmethod
    def _extract_state_delivery(pdp: dict) -> str | None:
        """Extract delivery info from state."""
        delivery = pdp.get("serviceability") or pdp.get("deliveryInfo") or {}
        if isinstance(delivery, dict):
            edd = delivery.get("edd") or delivery.get("estimatedDelivery")
            if edd:
                return str(edd)
        if isinstance(delivery, str):
            return delivery
        return None

    # ------------------------------------------------------------------
    # JSON-LD builder
    # ------------------------------------------------------------------

    def _build_from_json_ld(
        self, response, category_slug: str | None, external_id: str | None
    ) -> ProductItem | None:
        """Build ProductItem from JSON-LD structured data."""
        for script_text in response.css(
            'script[type="application/ld+json"]::text'
        ).getall():
            try:
                ld = json.loads(script_text)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(ld, list):
                ld = next(
                    (i for i in ld if isinstance(i, dict) and i.get("@type") == "Product"),
                    None,
                )
                if not ld:
                    continue
            if not isinstance(ld, dict) or ld.get("@type") != "Product":
                continue

            name = ld.get("name")
            sku = ld.get("sku") or external_id
            if not name or not sku:
                continue

            offers = ld.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}
            price = self._parse_price(offers.get("price") or offers.get("lowPrice"))
            mrp = self._parse_price(offers.get("highPrice"))

            brand_data = ld.get("brand") or {}
            brand = (
                brand_data.get("name")
                if isinstance(brand_data, dict)
                else str(brand_data) if brand_data else None
            )

            images = ld.get("image") or []
            if isinstance(images, str):
                images = [images]

            # Rating
            rating = None
            review_count = None
            ar = ld.get("aggregateRating")
            if isinstance(ar, dict):
                try:
                    rating = (
                        Decimal(str(ar["ratingValue"])) if ar.get("ratingValue") else None
                    )
                except (InvalidOperation, ValueError):
                    pass
                try:
                    review_count = (
                        int(ar["reviewCount"]) if ar.get("reviewCount") else None
                    )
                except (ValueError, TypeError):
                    pass

            in_stock = "OutOfStock" not in (offers.get("availability") or "")

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url.split("?")[0],
                title=str(name).strip(),
                brand=str(brand).strip() if brand else None,
                price=price,
                mrp=mrp,
                images=[i for i in images if isinstance(i, str)],
                rating=rating,
                review_count=review_count,
                specs={},
                seller_name="Myntra",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="Myntra",
                category_slug=category_slug or self._resolve_category_from_url(
                    response.url
                ),
                about_bullets=[],
                offer_details=[],
                raw_html_path=None,
                description=ld.get("description"),
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
    # DOM builder
    # ------------------------------------------------------------------

    def _build_from_dom(
        self,
        response,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Fallback: extract product data from rendered DOM."""
        title = None
        for sel in [
            "h1.pdp-title::text",
            "h1.pdp-name::text",
            ".pdp-title::text",
            "h1::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                title = text.strip()
                break
        if not title:
            return None

        pid = external_id
        if not pid:
            return None

        # Brand
        brand = None
        for sel in [
            "h1.pdp-title .pdp-title-brand::text",
            ".pdp-name .pdp-brand::text",
            "a.pdp-goToShop::text",
            "h3.product-brand::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                brand = text.strip()
                break

        # Selling price
        price = None
        for sel in [
            "span.pdp-price strong::text",
            ".pdp-discount-container span.pdp-price::text",
            "span.product-discountedPrice::text",
        ]:
            text = response.css(sel).get()
            if text:
                price = self._parse_price(text)
                if price:
                    break

        # MRP
        mrp = None
        for sel in [
            "span.pdp-mrp s::text",
            "span.pdp-price span.pdp-mrp::text",
            "span.product-strike::text",
        ]:
            text = response.css(sel).get()
            if text:
                mrp = self._parse_price(text)
                if mrp:
                    break

        # Images
        images: list[str] = []
        for sel in [
            "div.image-grid-image::attr(style)",
            "img.pdp-image::attr(src)",
            ".image-grid-image img::attr(src)",
            ".image-grid-imageContainer img::attr(src)",
        ]:
            for val in response.css(sel).getall():
                if "url(" in val:
                    match = re.search(r'url\(["\']?(.+?)["\']?\)', val)
                    if match:
                        images.append(match.group(1))
                elif val and not val.startswith("data:"):
                    images.append(val)

        # Rating
        rating = None
        review_count = None
        for sel in [
            ".index-overallRating div::text",
            ".index-overallRating span::text",
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        rating = Decimal(match.group(1))
                    except (InvalidOperation, ValueError):
                        pass
                    break

        for sel in [
            ".index-ratingsCount::text",
            ".index-ratingsContainer span::text",
        ]:
            text = response.css(sel).get()
            if text:
                nums = re.findall(r"[\d,]+", text)
                if nums:
                    try:
                        review_count = int(nums[0].replace(",", ""))
                    except ValueError:
                        pass
                    break

        # Specs
        specs: dict[str, str] = {}
        for row in response.css(
            ".index-tableContainer tr, .pdp-sizeFitDesc tr"
        ):
            cells = row.css("td::text").getall()
            if len(cells) >= 2:
                specs[cells[0].strip()] = cells[1].strip()

        # Sizes from DOM
        sizes = response.css(
            ".size-buttons-unified-size::text, "
            ".size-buttons-size-body button::text"
        ).getall()
        cleaned_sizes = [s.strip() for s in sizes if s.strip()]
        if cleaned_sizes:
            specs["sizes_available"] = ", ".join(cleaned_sizes)

        # Description
        description = response.css(
            ".pdp-product-description-content::text"
        ).get()
        if description:
            description = description.strip()

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=response.url.split("?")[0],
            title=title,
            brand=brand,
            price=price,
            mrp=mrp,
            images=images[:10],
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name="Myntra",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Myntra",
            category_slug=category_slug or self._resolve_category_from_url(
                response.url
            ),
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=None,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=self._extract_breadcrumbs(response),
            variant_options=[],
            country_of_origin=self._find_spec(specs, ["Country of Origin"]),
            manufacturer=self._find_spec(specs, ["Manufacturer"]) or brand,
            model_number=self._find_spec(
                specs, ["Article Number", "Style Code"]
            ),
            weight=self._find_spec(specs, ["Weight"]),
            dimensions=self._find_spec(specs, ["Dimensions"]),
        )

    def _build_from_listing(
        self,
        listing: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from listing page data (less detailed)."""
        name = listing.get("productName") or listing.get("name")
        pid = external_id or str(listing.get("productId") or listing.get("id") or "")
        if not name or not pid:
            return None

        price = self._parse_price(
            listing.get("discountedPrice") or listing.get("price")
        )
        mrp = self._parse_price(listing.get("mrp"))
        brand = listing.get("brand") or listing.get("brandName")

        images: list[str] = []
        for img in listing.get("images") or []:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                src = img.get("src") or img.get("url")
                if src:
                    images.append(src)
        search_img = listing.get("searchImage")
        if isinstance(search_img, str) and search_img not in images:
            images.append(search_img)

        # Rating from listing
        rating = None
        review_count = None
        rv = listing.get("rating") or listing.get("averageRating")
        if rv is not None:
            try:
                rating = Decimal(str(rv))
            except (InvalidOperation, ValueError):
                pass
        rc = listing.get("ratingCount") or listing.get("reviewCount")
        if rc is not None:
            try:
                review_count = int(rc)
            except (ValueError, TypeError):
                pass

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url.split("?")[0],
            title=str(name).strip(),
            brand=str(brand).strip() if brand else None,
            price=price,
            mrp=mrp,
            images=[i for i in images if i],
            rating=rating,
            review_count=review_count,
            specs={},
            seller_name="Myntra",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Myntra",
            category_slug=category_slug or self._resolve_category_from_url(url),
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

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_breadcrumbs(response) -> list[str]:
        """Extract navigation breadcrumbs from DOM."""
        crumbs = response.css(
            ".breadcrumb a::text, .breadcrumbs-list a::text, "
            "nav.breadcrumbs a::text"
        ).getall()
        return [c.strip() for c in crumbs if c.strip()]

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value to Decimal in paisa (rupees × 100)."""
        if price_val is None:
            return None
        try:
            val_str = str(price_val).replace(",", "").replace("₹", "").strip()
            match = PRICE_RE.search(val_str)
            if not match:
                return None
            rupees = Decimal(match.group().replace(",", ""))
            return rupees * 100 if rupees > 0 else None
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _is_blocked(response) -> bool:
        """Detect PerimeterX block, CAPTCHA, or empty page."""
        if response.status in (403, 429, 503):
            return True
        body = response.text or ""
        if len(body) < 1000:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        # PerimeterX-specific markers
        body_lower = body[:5000].lower()
        px_markers = [
            "px-captcha",
            "press & hold",
            "window._pxappid",
            "perimeterx",
            "human challenge",
        ]
        return any(m in body_lower for m in px_markers)

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract Whydud category slug from Myntra URL path."""
        path = url.split("?")[0].split("/")[-1].lower()
        if path in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[path]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in url.lower():
                return slug
        return "fashion"

    @staticmethod
    def _find_spec(specs: dict, keys: list[str]) -> str | None:
        """Extract a value from specs dict by trying multiple key names."""
        for key in keys:
            if key in specs:
                val = specs[key]
                if isinstance(val, str):
                    return val
        return None
