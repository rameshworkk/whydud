"""AJIO spider — camoufox-based scraper for Akamai Bot Manager bypass.

Architecture:
  AJIO (Reliance Retail) is a React SPA protected by Akamai Bot Manager.
  All HTTP requests (curl_cffi, Playwright headless/headed + stealth) return
  403 Access Denied.  Only camoufox (anti-detection Firefox) passes.

  Strategy:
    1. Category-based discovery: /{slug}/c/{code} via camoufox → product URLs
    2. Product detail pages: camoufox renders PDP → JSON-LD first, CSS fallback
    3. Fallback: DOM parsing for title, prices, images, rating

  Anti-bot: Akamai Bot Manager (aggressive — blocks Playwright + stealth + proxy)
  All prices in RUPEES — converted to paisa (* 100) before yielding.

URL patterns:
  Category: /men-t-shirts/c/830216001  → 20-45 products per page
  Product:  /brand-slug/p/product_code_color
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

PRODUCT_CODE_RE = re.compile(r"/p/([a-zA-Z0-9_]+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")
RATING_NUM_RE = re.compile(r"([\d.]+)")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review)", re.IGNORECASE)

MARKETPLACE_SLUG = "ajio"

# ---------------------------------------------------------------------------
# AJIO category slug → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "men-t-shirts": "fashion",
    "men-shirts": "fashion",
    "men-jeans": "fashion",
    "women-kurtas": "fashion",
    "women-tops": "fashion",
    "women-dresses": "fashion",
    "men-shoes": "fashion",
    "women-shoes": "fashion",
    "bags-wallets": "fashion",
    "watches": "fashion",
}

# ---------------------------------------------------------------------------
# Seed category URLs — (category_slug, category_code, max_pages)
# ---------------------------------------------------------------------------

_STD = 5  # pages per category (conservative for Akamai)

SEED_CATEGORIES: list[tuple[str, str, int]] = [
    ("men-t-shirts", "830216001", _STD),
    ("men-shirts", "830216003", _STD),
    ("men-jeans", "830216009", _STD),
    ("women-kurtas", "830318001", _STD),
    ("women-tops", "830218001", _STD),
    ("women-dresses", "830218010", _STD),
    ("men-shoes", "830116001", _STD),
    ("women-shoes", "830118001", _STD),
    ("bags-wallets", "830416001", _STD),
    ("watches", "830516001", _STD),
]

MAX_LISTING_PAGES = 5


# ---------------------------------------------------------------------------
# Camoufox downloader middleware
# ---------------------------------------------------------------------------


class AJIOCamoufoxMiddleware:
    """Scrapy downloader middleware using camoufox (anti-detection Firefox).

    Camoufox bypasses Akamai Bot Manager which blocks Playwright, curl_cffi,
    and even headed Chrome with stealth patches.  It achieves this by using a
    patched Firefox binary with realistic fingerprints.

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

        # On Windows, Playwright/camoufox needs ProactorEventLoop for
        # subprocess creation.  Scrapy forces SelectorEventLoop, but we can
        # set the policy here so the sync API's internal event loop uses
        # Proactor.  This is safe because Scrapy already created its loop.
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from camoufox.sync_api import Camoufox

        self._camoufox_cm = Camoufox(headless=True)
        self._context = self._camoufox_cm.__enter__()
        logger.info("Camoufox browser started for AJIO spider (thread pool)")

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
        """Intercept requests to ajio.com and render via camoufox."""
        if request.meta.get("skip_camoufox"):
            return None
        if "ajio.com" not in request.url:
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
                # Use a thread to close the browser so greenlet stays happy
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


class AJIOSpider(BaseWhydudSpider):
    """Scrapes AJIO.com — fashion marketplace with aggressive Akamai.

    Uses camoufox (anti-detection Firefox) instead of Playwright.
    Two-phase: category pages for discovery → product pages for detail.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated category URLs to scrape directly.
      max_pages     — max listing pages per category (default 5).
    """

    name = "ajio"
    allowed_domains = ["ajio.com", "www.ajio.com"]

    QUICK_MODE_CATEGORIES = 3

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
            "apps.scraping.spiders.ajio_spider.AJIOCamoufoxMiddleware": 100,
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

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._blocked_count: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"AJIO spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"blocked={self._blocked_count}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests — Phase 1: Category pages via camoufox
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit requests for AJIO category listing pages."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        url_list = self._load_urls()

        if self._category_urls:
            # Direct URLs — could be product or category
            for url in self._category_urls:
                if "/p/" in url:
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
                    yield scrapy.Request(
                        url,
                        callback=self.parse_listing_page,
                        errback=self.handle_error,
                        meta={
                            "category_slug": self._resolve_category_from_url(url),
                            "camoufox_wait_ms": 12000,
                            "max_pages": self._max_pages_override or MAX_LISTING_PAGES,
                            "base_url": url,
                        },
                        dont_filter=True,
                    )
        else:
            for url, cat_slug, max_pg in url_list:
                self._pages_followed[url] = 0
                self.logger.info(f"Queuing AJIO category ({max_pg} pages): {cat_slug}")
                yield scrapy.Request(
                    url,
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    meta={
                        "category_slug": cat_slug,
                        "camoufox_wait_ms": 12000,
                        "max_pages": max_pg,
                        "base_url": url,
                    },
                    dont_filter=True,
                )

        count = len(self._category_urls) or len(url_list)
        self.logger.info(f"Queued {count} AJIO requests (camoufox)")

    def _load_urls(self) -> list[tuple[str, str, int]]:
        """Resolve the list of (url, category_slug, max_pages) to crawl."""
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_CATEGORIES} categories "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (
                        f"https://www.ajio.com/{slug}/c/{code}",
                        slug,
                        self._max_pages_override,
                    )
                    for slug, code, _ in SEED_CATEGORIES[: self.QUICK_MODE_CATEGORIES]
                ]
            return [
                (f"https://www.ajio.com/{slug}/c/{code}", slug, self._max_pages_override)
                for slug, code, _ in SEED_CATEGORIES
            ]

        return [
            (f"https://www.ajio.com/{slug}/c/{code}", slug, max_pg)
            for slug, code, max_pg in SEED_CATEGORIES
        ]

    # ------------------------------------------------------------------
    # Phase 1: Listing page
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from an AJIO category listing page."""
        self._listing_pages_scraped += 1
        base_url = response.meta.get("base_url", response.url)
        category_slug = response.meta.get("category_slug")
        max_pages = response.meta.get("max_pages", MAX_LISTING_PAGES)

        # Block detection
        if self._is_blocked(response):
            self._blocked_count += 1
            self.logger.warning(
                f"AJIO blocked listing: HTTP {response.status} on {response.url}"
            )
            self.items_failed += 1
            return

        # Extract product links (URLs containing /p/)
        product_links = response.css('a[href*="/p/"]::attr(href)').getall()

        seen: set[str] = set()
        unique_links: list[str] = []
        for link in product_links:
            full = response.urljoin(link)
            canon = full.split("?")[0]
            if canon not in seen:
                seen.add(canon)
                unique_links.append(full)

        if not unique_links:
            self.logger.warning(f"No product links found on {response.url}")
            return

        self.logger.info(f"Found {len(unique_links)} products on {response.url}")

        for link in unique_links:
            yield scrapy.Request(
                link,
                callback=self.parse_product_page,
                errback=self.handle_error,
                meta={
                    "category_slug": category_slug,
                    "camoufox_wait_ms": 10000,
                },
                dont_filter=True,
            )

        # Pagination
        pages_so_far = self._pages_followed.get(base_url, 0) + 1
        self._pages_followed[base_url] = pages_so_far

        if pages_so_far < max_pages:
            next_url = self._build_next_page_url(response.url, pages_so_far + 1)
            self.logger.info(
                f"Following AJIO page {pages_so_far + 1}/{max_pages}: {next_url}"
            )
            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                meta={
                    "category_slug": category_slug,
                    "camoufox_wait_ms": 12000,
                    "max_pages": max_pages,
                    "base_url": base_url,
                },
                dont_filter=True,
            )

    @staticmethod
    def _build_next_page_url(current_url: str, page_num: int) -> str:
        """Build next page URL for AJIO category pagination."""
        base = re.sub(r"[?&](?:page|currentPage)=\d+", "", current_url)
        separator = "&" if "?" in base else "?"
        return f"{base}{separator}page={page_num}"

    # ------------------------------------------------------------------
    # Phase 2: Product detail page
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from an AJIO product detail page."""
        if self._is_blocked(response):
            self._blocked_count += 1
            self.logger.warning(
                f"AJIO blocked product: HTTP {response.status} on {response.url}"
            )
            self.items_failed += 1
            return

        product_code = self._extract_product_code(response)
        if not product_code:
            self.logger.warning(f"Could not extract product code from {response.url}")
            self.items_failed += 1
            return

        ld_json = self._parse_json_ld(response)
        yield from self._build_item(response, product_code, ld_json)

    def _build_item(self, response, product_code: str, ld_json: dict | None):
        """Build and yield a ProductItem from JSON-LD + CSS data."""
        title = self._extract_title(response, ld_json)
        if not title:
            self.logger.warning(f"No title found for {product_code}")
            self.items_failed += 1
            return

        item = ProductItem()
        item["marketplace_slug"] = MARKETPLACE_SLUG
        item["external_id"] = product_code
        item["url"] = self._canonical_url(response.url)
        item["title"] = title
        item["brand"] = self._extract_brand(response, ld_json)
        item["price"] = self._extract_price(response, ld_json)
        item["mrp"] = self._extract_mrp(response, ld_json)
        item["images"] = self._extract_images(response, ld_json)
        item["rating"] = self._extract_rating(response, ld_json)
        item["review_count"] = self._extract_review_count(response)
        item["specs"] = self._extract_specs(response)
        item["seller_name"] = "AJIO"
        item["seller_rating"] = None
        item["in_stock"] = self._extract_availability(response, ld_json)
        item["fulfilled_by"] = "AJIO"
        item["category_slug"] = response.meta.get("category_slug")
        item["about_bullets"] = []
        item["offer_details"] = self._extract_offers(response)
        item["raw_html_path"] = None

        # Extended fields
        item["description"] = self._extract_description(response, ld_json)
        item["warranty"] = None
        item["delivery_info"] = self._extract_delivery_info(response)
        item["return_policy"] = self._extract_return_policy(response)
        item["breadcrumbs"] = self._extract_breadcrumbs(response)
        item["variant_options"] = self._extract_variants(response)

        specs = item["specs"]
        item["country_of_origin"] = self._extract_from_specs(
            specs, ["Country of Origin", "country of origin", "Country Of Origin"]
        )
        item["manufacturer"] = self._extract_from_specs(
            specs, ["Manufacturer", "manufacturer"]
        )
        item["model_number"] = self._extract_from_specs(
            specs, ["Model Number", "Model Name", "Article Code"]
        )
        item["weight"] = self._extract_from_specs(specs, ["Weight", "Net Weight"])
        item["dimensions"] = self._extract_from_specs(specs, ["Dimensions"])

        self.items_scraped += 1
        self._products_extracted += 1
        self._product_pages_scraped += 1
        yield item

    # ------------------------------------------------------------------
    # Helpers — block detection
    # ------------------------------------------------------------------

    @staticmethod
    def _is_blocked(response) -> bool:
        """Detect Akamai block or empty page."""
        if response.status in (403, 429, 503):
            return True
        if len(response.text or "") < 1000:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        return "access denied" in title or "blocked" in title

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_ld(response) -> dict | None:
        """Extract the first schema.org Product JSON-LD block from the page."""
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, ValueError):
                continue

            if isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
            elif isinstance(data, dict):
                if data.get("@type") == "Product":
                    return data
                for obj in data.get("@graph", []):
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
        return None

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_product_code(response) -> str | None:
        """Extract product code from AJIO URL — e.g. ``460259543_blue``."""
        match = PRODUCT_CODE_RE.search(response.url)
        return match.group(1) if match else None

    @staticmethod
    def _canonical_url(url: str) -> str:
        """Return canonical product URL (strip tracking params)."""
        return url.split("?")[0]

    @staticmethod
    def _extract_title(response, ld_json: dict | None) -> str | None:
        """Extract product title."""
        if ld_json and ld_json.get("name"):
            return ld_json["name"].strip()
        for sel in [
            "h1.prod-name::text",
            ".prod-name::text",
            "h1::text",
            "h2.prod-name::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    @staticmethod
    def _extract_brand(response, ld_json: dict | None) -> str | None:
        """Extract brand name."""
        if ld_json:
            brand_obj = ld_json.get("brand")
            if isinstance(brand_obj, dict) and brand_obj.get("name"):
                return brand_obj["name"].strip()
            if isinstance(brand_obj, str) and brand_obj.strip():
                return brand_obj.strip()
        for sel in [
            ".brand-name::text",
            ".prod-brand::text",
            "h2.brand-name::text",
            "a.brand-name::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    def _extract_price(self, response, ld_json: dict | None) -> Decimal | None:
        """Extract current sale price in paisa."""
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                price = self._json_ld_price(offers)
                if price is not None:
                    return price
            elif isinstance(offers, list):
                for offer in offers:
                    price = self._json_ld_price(offer)
                    if price is not None:
                        return price

        for sel in [
            ".prod-sp::text",
            ".prod-price .prod-sp::text",
            "span.prod-sp::text",
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price
        return None

    def _extract_mrp(self, response, ld_json: dict | None) -> Decimal | None:
        """Extract MRP (maximum retail price) in paisa."""
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                high = offers.get("highPrice")
                if high:
                    try:
                        return Decimal(str(high)) * 100
                    except InvalidOperation:
                        pass

        for sel in [
            ".prod-cp::text",
            ".prod-price .prod-cp::text",
            "span.prod-cp::text",
        ]:
            text = response.css(sel).get()
            mrp = self._parse_price_text(text)
            if mrp is not None:
                return mrp
        return None

    @staticmethod
    def _extract_images(response, ld_json: dict | None) -> list[str]:
        """Extract product image URLs."""
        images: list[str] = []
        if ld_json:
            img = ld_json.get("image")
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, list):
                images.extend(img)

        for sel in [
            ".zoom-wrap img::attr(src)",
            ".img-container img::attr(src)",
            ".rilrtl-lazy-img::attr(src)",
            "img.rilrtl-lazy-img::attr(src)",
            ".pdp-img-container img::attr(src)",
        ]:
            for src in response.css(sel).getall():
                if src and src not in images:
                    images.append(src)

        seen: set[str] = set()
        deduped: list[str] = []
        for img in images:
            if img and img not in seen:
                seen.add(img)
                deduped.append(img)
        return deduped

    @staticmethod
    def _extract_rating(response, ld_json: dict | None) -> Decimal | None:
        """Extract aggregate rating (0-5)."""
        if ld_json:
            ar = ld_json.get("aggregateRating")
            if isinstance(ar, dict):
                val = ar.get("ratingValue")
                if val is not None:
                    try:
                        return Decimal(str(val))
                    except InvalidOperation:
                        pass

        for sel in [
            ".prod-rating span::text",
            ".rating-value::text",
            ".star-rating::text",
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    @staticmethod
    def _extract_review_count(response) -> int | None:
        """Extract review/rating count."""
        for sel in [
            ".prod-rating-count::text",
            ".rating-count::text",
        ]:
            text = response.css(sel).get()
            if text:
                match = REVIEW_COUNT_RE.search(text)
                if match:
                    return int(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_specs(response) -> dict:
        """Extract product specifications."""
        specs: dict[str, str] = {}

        # Pattern 1: detail-list / prod-desc table
        for row in response.css(".detail-list li, .prod-desc table tr, .detail-info li"):
            key = row.css(
                "::first-child::text, td:first-child::text, .info-title::text"
            ).get()
            val = row.css(
                "::last-child::text, td:last-child::text, .info-desc::text"
            ).get()
            if key and val:
                specs[key.strip().rstrip(":")] = val.strip()

        # Pattern 2: pdp-details pairs
        for detail in response.css(".pdp-details .detail-row, .prod-details .detail-wrap"):
            key = detail.css(".detail-label::text, .detail-title::text").get()
            val = detail.css(".detail-value::text, .detail-desc::text").get()
            if key and val:
                specs[key.strip().rstrip(":")] = val.strip()

        # Sizes — stored as comma-separated string (pipeline expects str values)
        sizes = response.css(
            ".size-variant-item::text, .size-swatch::text, .size-btn::text"
        ).getall()
        cleaned_sizes = [s.strip() for s in sizes if s.strip()]
        if cleaned_sizes:
            specs["sizes_available"] = ", ".join(cleaned_sizes)

        # Colors — stored as comma-separated string
        colors = response.css(
            ".color-variant-item::attr(title), "
            ".color-swatch::attr(title), "
            ".color-btn::attr(title)"
        ).getall()
        cleaned_colors = [c.strip() for c in colors if c.strip()]
        if cleaned_colors:
            specs["colors_available"] = ", ".join(cleaned_colors)

        return specs

    @staticmethod
    def _extract_availability(response, ld_json: dict | None) -> bool:
        """Determine if the product is in stock."""
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                avail = offers.get("availability", "")
                if "InStock" in avail:
                    return True
                if "OutOfStock" in avail:
                    return False

        body = response.text[:5000] if response.text else ""
        if "out of stock" in body.lower() or "sold out" in body.lower():
            return False
        return True

    @staticmethod
    def _extract_offers(response) -> list[dict]:
        """Extract bank offers, coupons, promos."""
        offers: list[dict] = []
        for offer_el in response.css(
            ".offer-item, .promo-card, .bank-offer, .offer-container .offer-text"
        ):
            text = offer_el.css("::text").getall()
            full_text = " ".join(t.strip() for t in text if t.strip())
            if full_text:
                offers.append({"type": "offer", "text": full_text})
        return offers

    @staticmethod
    def _extract_description(response, ld_json: dict | None) -> str | None:
        """Extract product description."""
        if ld_json and ld_json.get("description"):
            return ld_json["description"].strip()
        for sel in [
            ".prod-desc::text",
            ".pdp-product-description::text",
            ".product-description::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    @staticmethod
    def _extract_delivery_info(response) -> str | None:
        """Extract delivery information."""
        for sel in [".delivery-info::text", ".edd-text::text", ".delivery-text::text"]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    @staticmethod
    def _extract_return_policy(response) -> str | None:
        """Extract return policy text."""
        for sel in [".return-policy::text", ".return-exchange::text", ".return-info::text"]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    @staticmethod
    def _extract_breadcrumbs(response) -> list[str]:
        """Extract navigation breadcrumbs."""
        crumbs = response.css(
            ".breadcrumb a::text, .breadcrumb-item::text, .breadcrumb li::text"
        ).getall()
        return [c.strip() for c in crumbs if c.strip()]

    @staticmethod
    def _extract_variants(response) -> list[dict]:
        """Extract color/size variant options."""
        variants: list[dict] = []
        for color_el in response.css(
            ".color-variant-item, .color-swatch, .color-container .color-btn"
        ):
            color = (
                color_el.css("::attr(title)").get()
                or color_el.css("::text").get()
            )
            href = color_el.css("::attr(href)").get()
            if color:
                v: dict = {"type": "color", "value": color.strip()}
                if href:
                    v["url"] = href
                variants.append(v)

        for size_el in response.css(".size-variant-item, .size-swatch, .size-btn"):
            size = size_el.css("::text").get()
            if size and size.strip():
                variants.append({"type": "size", "value": size.strip()})

        return variants

    @staticmethod
    def _extract_from_specs(specs: dict, keys: list[str]) -> str | None:
        """Extract a specific field from specs dict by trying multiple key names."""
        for key in keys:
            if key in specs:
                val = specs[key]
                if isinstance(val, str):
                    return val
        return None

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract Whydud category slug from AJIO URL."""
        match = re.search(r"ajio\.com/([^/]+)/c/", url)
        if match:
            return KEYWORD_CATEGORY_MAP.get(match.group(1), "fashion")
        return "fashion"

    # ------------------------------------------------------------------
    # Price parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _json_ld_price(offers_dict: dict) -> Decimal | None:
        """Parse price from a JSON-LD offers object → paisa."""
        for key in ("price", "lowPrice"):
            raw = offers_dict.get(key)
            if raw is not None:
                try:
                    return Decimal(str(raw)) * 100
                except InvalidOperation:
                    pass
        return None

    @staticmethod
    def _parse_price_text(text: str | None) -> Decimal | None:
        """Parse Indian currency format (₹1,00,000) to paisa."""
        if not text:
            return None
        cleaned = re.sub(r"[₹,\s]", "", text).strip()
        match = PRICE_RE.search(cleaned)
        if match:
            try:
                return Decimal(match.group(0).replace(",", "")) * 100
            except InvalidOperation:
                pass
        return None
