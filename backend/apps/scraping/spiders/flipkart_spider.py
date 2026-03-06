"""Flipkart spider — camoufox-based scraper for anti-bot bypass.

Architecture:
  Flipkart is a React SPA with aggressive bot detection that blocks
  Playwright Chromium with 500/403 errors.  Camoufox (anti-detection
  Firefox patched at C++ level) bypasses these blocks.

  Strategy:
    Phase 1: Listing pages (/search?q=...) via camoufox — React-rendered.
    Phase 2: Product detail pages try PLAIN HTTP first (JSON-LD in HTML).
             Falls back to camoufox if HTTP is blocked or data incomplete.

  Data sources (priority order):
    1. JSON-LD structured data — title, price, brand, rating, images
    2. window.__INITIAL_STATE__ (Redux) — MRP, seller, variants, availability
    3. CSS/XPath fallbacks — specs, highlights, offers, warranty

Sprint 2, Week 5.
"""

from __future__ import annotations

import json
import logging
import os
import random
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlparse

import scrapy
from scrapy import signals
from scrapy.http import HtmlResponse, TextResponse

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPID_RE = re.compile(r"/p/(itm[a-zA-Z0-9]+)")
PRICE_RE = re.compile(r"[\d,.]+")
RATING_NUM_RE = re.compile(r"([\d.]+)")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review)", re.IGNORECASE)

MARKETPLACE_SLUG = "flipkart"

# NOTE: KEYWORD_CATEGORY_MAP removed — category resolution now handled
# centrally by apps.products.category_mapper.resolve_canonical_category()


# Seed category search URLs — used when no ScraperJob provides URLs.
# Format: (url, max_pages) — controls pagination depth per category.
# Top categories get 30 pages (~480 products), standard get 20 pages (~320 products).

_TOP = 30   # pages for top categories
_STD = 20   # pages for standard categories

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones & Accessories (TOP) ──────────────────────────────────
    ("https://www.flipkart.com/search?q=smartphones&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=phone+cases+covers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=screen+protectors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=power+banks&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=mobile+chargers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=mobile+holders+stands&sort=popularity", _STD),
    # ── Computers & Peripherals (TOP) ────────────────────────────────────
    ("https://www.flipkart.com/search?q=laptops&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=tablets&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=monitors&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=computer+keyboards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=computer+mouse&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=printers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=routers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=external+hard+drives&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=pen+drives&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=graphics+cards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=webcams&sort=popularity", _STD),
    # ── Audio (TOP) ──────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=headphones&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=earbuds+tws&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=bluetooth+speakers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=soundbars&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=microphones&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=home+theatre+systems&sort=popularity", _STD),
    # ── Wearables (TOP) ──────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=smartwatches&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=fitness+bands&sort=popularity", _STD),
    # ── Cameras & Photography ────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=cameras&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=camera+lenses&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=camera+tripods&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=action+cameras&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=drones+cameras&sort=popularity", _STD),
    # ── TVs & Entertainment (TOP) ────────────────────────────────────────
    ("https://www.flipkart.com/search?q=televisions&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=projectors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=streaming+devices&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=tv+wall+mounts&sort=popularity", _STD),
    # ── Large Appliances (TOP) ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=refrigerators&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=washing+machines&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=air+conditioners&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=microwave+ovens&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dishwashers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=water+heaters+geysers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=chimneys&sort=popularity", _STD),
    # ── Small Appliances ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=air+purifiers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=water+purifiers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=vacuum+cleaners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=robot+vacuum+cleaners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=mixer+grinders&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=induction+cooktops&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=electric+kettles&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=air+fryers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=coffee+machines&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=irons+steamers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=fans&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=room+heaters&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=juicer+mixer+grinder&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hand+blenders&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=sandwich+makers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=toasters&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=rice+cookers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=pressure+cookers&sort=popularity", _STD),
    # ── Personal Care & Grooming (TOP) ───────────────────────────────────
    ("https://www.flipkart.com/search?q=trimmers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=electric+shavers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hair+dryers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hair+straighteners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=electric+toothbrushes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=epilators&sort=popularity", _STD),
    # ── Fitness & Sports ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=treadmills&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=exercise+bikes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dumbbells+weights&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=yoga+mats&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gym+equipment&sort=popularity", _STD),
    # ── Home & Furniture (TOP) ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=mattresses&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=office+chairs&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=study+tables&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=beds&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=sofas&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=shoe+racks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dining+tables&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=wardrobes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=bean+bags&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=curtains&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=bedsheets&sort=popularity", _STD),
    # ── Smart Home & Security (TOP) ──────────────────────────────────────
    ("https://www.flipkart.com/search?q=smart+plugs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=smart+bulbs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=security+cameras&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=smart+door+locks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=video+doorbells&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=smart+speakers&sort=popularity", _STD),
    # ── Gaming (TOP) ─────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=gaming+laptops&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=gaming+monitors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+headsets&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+controllers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+chairs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+consoles&sort=popularity", _STD),
    # ── Storage & Networking ─────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=ssd+internal&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=memory+cards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=wifi+mesh+systems&sort=popularity", _STD),
    # ── Baby & Kids ──────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=baby+strollers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+seats+baby&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=baby+monitors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=baby+toys&sort=popularity", _STD),
    # ── Car & Bike Accessories ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=dash+cameras&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+chargers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+air+purifiers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=tyre+inflators&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+accessories&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=helmet&sort=popularity", _STD),
    # ── Musical Instruments ──────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=guitars&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=keyboards+pianos&sort=popularity", _STD),
    # ── Luggage & Bags ───────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=laptop+bags+backpacks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=suitcases+trolley&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=handbags&sort=popularity", _STD),
    # ── Books ────────────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=books+bestsellers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=school+bags&sort=popularity", _STD),
    # ── Fashion & Accessories ────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=sunglasses&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=watches+men&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=watches+women&sort=popularity", _STD),
    # ── Kitchen & Dining ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=cookware+sets&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=water+bottles&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=lunch+boxes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=kitchen+storage&sort=popularity", _STD),
]

MAX_LISTING_PAGES = 5


# ---------------------------------------------------------------------------
# Camoufox downloader middleware
# ---------------------------------------------------------------------------


class FlipkartCamoufoxMiddleware:
    """Scrapy downloader middleware using camoufox (anti-detection Firefox).

    Only intercepts requests with ``meta["camoufox"] = True``.
    Manages a single persistent browser context with optional proxy.

    CRITICAL: All camoufox/Playwright sync API calls MUST run on the SAME
    dedicated thread.  Playwright's sync layer uses greenlets that are bound
    to the OS thread that created them — dispatching to the default
    ThreadPoolExecutor (which may pick *any* thread) causes
    ``greenlet.error: Cannot switch to a different thread``.

    Solution: a single-worker ``ThreadPoolExecutor`` pins every browser
    operation to one thread for the lifetime of the spider.
    """

    def __init__(self) -> None:
        import concurrent.futures

        self._context = None
        self._camoufox_cm = None
        self._request_count = 0
        self._success_count = 0
        self._fail_count = 0
        # Single-thread executor — all camoufox ops are serialised here.
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="camoufox"
        )

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        middleware._crawler = crawler
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    # -- proxy helpers -----------------------------------------------------

    @staticmethod
    def _get_proxy() -> dict | None:
        """Read the first proxy from SCRAPING_PROXY_LIST env var."""
        proxy_list = os.environ.get("SCRAPING_PROXY_LIST", "").strip()
        if not proxy_list:
            return None
        first = proxy_list.split(",")[0].strip()
        if not first:
            return None
        parsed = urlparse(first)
        if not parsed.hostname or not parsed.port:
            return None
        proxy: dict = {"server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"}
        if parsed.username:
            proxy["username"] = parsed.username
        if parsed.password:
            proxy["password"] = parsed.password
        return proxy

    # -- browser lifecycle -------------------------------------------------

    def _ensure_browser(self) -> None:
        """Start camoufox browser (called ONLY on the dedicated worker thread)."""
        if self._context is not None:
            return

        import asyncio
        import sys

        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from camoufox.sync_api import Camoufox

        proxy = self._get_proxy()
        self._camoufox_cm = Camoufox(
            headless=True,
            proxy=proxy,
            geoip=bool(proxy),
            block_images=True,
            block_webrtc=True,
            os="windows",
            i_know_what_im_doing=True,
        )
        self._context = self._camoufox_cm.__enter__()
        logger.info(
            f"Camoufox browser started for Flipkart (proxy={'yes' if proxy else 'no'})"
        )

    def _fetch_page(
        self, url: str, wait_ms: int, wait_selector: str | None = None
    ) -> tuple[int, bytes]:
        """Render a page with camoufox (runs on the dedicated worker thread).

        Because the executor has max_workers=1, calls are automatically
        serialised and always execute on the same OS thread — no greenlet
        cross-thread switches can occur.
        """
        self._ensure_browser()
        page = self._context.new_page()
        try:
            resp = page.goto(url, wait_until="domcontentloaded", timeout=60000)
            status = resp.status if resp else 200

            # Wait for a specific element (e.g. product links on listings)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=15000)
                except Exception:
                    pass  # Proceed anyway — data may still be in HTML

            page.wait_for_timeout(wait_ms)
            content = page.content()
            return status, content.encode("utf-8")
        finally:
            page.close()

    def _close_browser(self) -> None:
        """Shut down camoufox (runs on the dedicated worker thread)."""
        if self._camoufox_cm is not None:
            self._camoufox_cm.__exit__(None, None, None)

    # -- Scrapy middleware hooks --------------------------------------------

    async def process_request(self, request, spider=None):
        """Intercept requests flagged with meta['camoufox'] = True."""
        if not request.meta.get("camoufox"):
            return None

        self._request_count += 1
        wait_ms = request.meta.get("camoufox_wait_ms", 5000)
        wait_selector = request.meta.get("camoufox_wait_selector")

        try:
            import asyncio

            loop = asyncio.get_event_loop()
            status, body = await loop.run_in_executor(
                self._executor, self._fetch_page, request.url, wait_ms, wait_selector
            )
            self._success_count += 1
            return HtmlResponse(
                url=request.url,
                status=status,
                body=body,
                request=request,
                encoding="utf-8",
            )
        except Exception as exc:
            self._fail_count += 1
            logger.warning(f"Camoufox request failed for {request.url[:80]}: {exc}")
            return HtmlResponse(
                url=request.url,
                status=503,
                body=b"",
                request=request,
                encoding="utf-8",
            )

    def spider_closed(self, spider=None):
        """Shut down camoufox browser cleanly on the dedicated thread."""
        if self._context is not None:
            try:
                future = self._executor.submit(self._close_browser)
                future.result(timeout=15)
            except Exception as exc:
                logger.warning(f"Error closing camoufox: {exc}")
            self._context = None
            self._camoufox_cm = None
        self._executor.shutdown(wait=False)
        logger.info(
            f"Camoufox middleware closed — {self._request_count} requests "
            f"({self._success_count} OK, {self._fail_count} failed)"
        )


# ---------------------------------------------------------------------------
# Spider
# ---------------------------------------------------------------------------


class FlipkartSpider(BaseWhydudSpider):
    """Scrapes Flipkart with camoufox (anti-detection Firefox).

    Phase 1: Listing pages via camoufox (React-rendered, lazy-loaded cards).
    Phase 2: Product detail pages try plain HTTP first (JSON-LD is in raw HTML).
             Falls back to camoufox only when HTTP is blocked or data incomplete.

    Spider arguments (passed via ``-a``):
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES (default 5).
      save_html     — "1" to save raw HTML for debugging.
    """

    name = "flipkart"
    allowed_domains = ["flipkart.com", "www.flipkart.com"]

    # Quick mode: only use first N categories when --max-pages <= 3
    QUICK_MODE_CATEGORIES = 10

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 3,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "HTTPERROR_ALLOWED_CODES": [403],
        # Disable scrapy_playwright — we use camoufox middleware instead.
        "DOWNLOAD_HANDLERS": {
            "https": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
            "http": "scrapy.core.downloader.handlers.http11.HTTP11DownloadHandler",
        },
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.middlewares.PlaywrightProxyMiddleware": None,
            "apps.scraping.spiders.flipkart_spider.FlipkartCamoufoxMiddleware": 100,
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
        save_html: str = "0",
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
        self._save_html = save_html == "1"
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}

        # Scrape stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._product_pages_plain_http: int = 0
        self._product_pages_camoufox: int = 0
        self._blocked_count: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Flipkart spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"plain_http={self._product_pages_plain_http}, "
            f"camoufox={self._product_pages_camoufox}, "
            f"blocked={self._blocked_count}, "
            f"failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests — Phase 1: camoufox for listings
    # ------------------------------------------------------------------

    async def start(self):
        """Emit requests for listing pages or direct product detail pages.

        Listing pages use camoufox (React-rendered). Product detail URLs
        (containing /p/itm) are routed directly to parse_product_page
        via plain HTTP first (JSON-LD), with camoufox fallback inside parser.

        Uses async ``start()`` (Scrapy 2.13+) instead of deprecated
        ``start_requests()``.
        """
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        product_count = 0
        listing_count = 0

        for url, max_pg in url_pairs:
            # Direct product URL → skip listing phase, go to detail parser
            if FPID_RE.search(url):
                product_count += 1
                yield scrapy.Request(
                    url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                )
                continue

            # Listing page — camoufox required
            listing_count += 1
            base = re.sub(r"[&?]page=\d+", "", url)
            self._max_pages_map[base] = max_pg
            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "camoufox": True,
                    "camoufox_wait_ms": 8000,
                    "camoufox_wait_selector": 'a[href*="/p/itm"]',
                    "category_slug": self._resolve_category_from_url(url),
                },
                dont_filter=True,
            )

        if product_count:
            self.logger.info(f"Queued {product_count} product URLs (plain HTTP → camoufox)")
        if listing_count:
            self.logger.info(f"Queued {listing_count} categories (camoufox)")

    def _load_urls(self) -> list[tuple[str, int]]:
        """Resolve the list of (url, max_pages) pairs to crawl.

        Priority: CLI ``category_urls`` > ScraperJob > seed categories.
        """
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]

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
            if self._max_pages_override <= 3:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_CATEGORIES} categories "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[: self.QUICK_MODE_CATEGORIES]
                ]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Phase 1: Listing page (search results / category pages)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from a Flipkart search/category page."""
        self._listing_pages_scraped += 1
        block_retries = response.meta.get("block_retries", 0)

        # Non-text response — can't parse with CSS/XPath
        if not isinstance(response, TextResponse):
            self.logger.warning(
                f"Non-text listing response — skipping {response.url[:80]}"
            )
            self._blocked_count += 1
            self.items_failed += 1
            return

        # Block detection: 403/429 status codes
        if response.status in (403, 429):
            if not response.css('a[href*="/p/itm"]'):
                self._blocked_count += 1
                max_retries = 2  # camoufox is stealthier — allow 2 retries
                if block_retries < max_retries:
                    self.logger.info(
                        f"Flipkart blocked listing HTTP {response.status} — "
                        f"retry {block_retries + 1}/{max_retries}: {response.url}"
                    )
                    yield scrapy.Request(
                        response.url,
                        callback=self.parse_listing_page,
                        errback=self.handle_error,
                        headers=self._make_headers(),
                        meta={
                            "camoufox": True,
                            "camoufox_wait_ms": 10000,
                            "camoufox_wait_selector": 'a[href*="/p/itm"]',
                            "category_slug": response.meta.get("category_slug"),
                            "block_retries": block_retries + 1,
                        },
                        dont_filter=True,
                        priority=-1,
                    )
                    return

                self.logger.warning(
                    f"Flipkart blocked listing page: HTTP {response.status} on {response.url}"
                )
                self.items_failed += 1
                return

        # Flipkart product links always contain /p/itm
        product_links = response.css('a[href*="/p/itm"]::attr(href)').getall()
        seen: set[str] = set()
        unique_links: list[str] = []
        for link in product_links:
            full = response.urljoin(link)
            canon = full.split("?")[0]
            if canon not in seen:
                seen.add(canon)
                unique_links.append(full)

        if not unique_links:
            if "Access Denied" in (response.text or "")[:1000]:
                self._blocked_count += 1
                max_retries = 2
                if block_retries < max_retries:
                    self.logger.info(
                        f"Flipkart Access Denied — retry {block_retries + 1}/{max_retries}: {response.url}"
                    )
                    yield scrapy.Request(
                        response.url,
                        callback=self.parse_listing_page,
                        errback=self.handle_error,
                        headers=self._make_headers(),
                        meta={
                            "camoufox": True,
                            "camoufox_wait_ms": 10000,
                            "camoufox_wait_selector": 'a[href*="/p/itm"]',
                            "category_slug": response.meta.get("category_slug"),
                            "block_retries": block_retries + 1,
                        },
                        dont_filter=True,
                        priority=-1,
                    )
                    return

                self.logger.warning(f"Flipkart Access Denied on {response.url}")
                self.items_failed += 1
                return
            self.logger.warning(f"No product links found on {response.url}")
            return

        self.logger.info(f"Found {len(unique_links)} products on {response.url}")

        category_slug = response.meta.get(
            "category_slug"
        ) or self._resolve_category_from_url(response.url)

        for link in unique_links:
            # Phase 2: Try plain HTTP first for product pages
            yield scrapy.Request(
                link,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={"category_slug": category_slug},
            )

        # Pagination
        base_url = re.sub(r"[&?]page=\d+", "", response.url)
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)
        if pages_so_far < max_for_category:
            next_link = self._find_next_page(response)
            if next_link:
                self._pages_followed[base_url] = pages_so_far + 1
                yield scrapy.Request(
                    response.urljoin(next_link),
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "camoufox": True,
                        "camoufox_wait_ms": 8000,
                        "camoufox_wait_selector": 'a[href*="/p/itm"]',
                        "category_slug": category_slug,
                    },
                )

    @staticmethod
    def _find_next_page(response) -> str | None:
        """Locate the "Next" pagination link."""
        for a in response.css("nav a"):
            text = a.css("::text").get("").strip().lower()
            if text == "next":
                return a.attrib.get("href")
        nav_link = response.xpath(
            '//a[.//span[contains(text(),"Next")]]/@href'
        ).get()
        return nav_link

    # ------------------------------------------------------------------
    # Phase 2: Product detail page (plain HTTP first → camoufox fallback)
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data — tries plain HTTP + JSON-LD first.

        If JSON-LD has title + price → sufficient, no camoufox needed.
        If incomplete and this was plain HTTP → retry with camoufox.
        If this was already camoufox → extract whatever we can.
        """
        self._product_pages_scraped += 1
        is_camoufox = response.meta.get("camoufox", False)

        if is_camoufox:
            self._product_pages_camoufox += 1
        else:
            self._product_pages_plain_http += 1

        # Non-text response (binary/bot-detection page) — promote to camoufox
        if not isinstance(response, TextResponse):
            if not is_camoufox:
                self.logger.info(
                    f"Non-text response — promoting to camoufox: {response.url[:80]}"
                )
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "camoufox": True,
                        "camoufox_wait_ms": 5000,
                        "category_slug": response.meta.get("category_slug"),
                    },
                    dont_filter=True,
                )
                return
            self.logger.warning(
                f"Non-text response even with camoufox — skipping {response.url[:80]}"
            )
            self.items_failed += 1
            return

        # Block detection: HTTP 403/429 on plain HTTP → promote to camoufox
        if response.status in (403, 429) and not is_camoufox:
            self.logger.info(
                f"HTTP {response.status} on product page — promoting to camoufox: {response.url}"
            )
            yield scrapy.Request(
                response.url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "camoufox": True,
                    "camoufox_wait_ms": 5000,
                    "category_slug": response.meta.get("category_slug"),
                },
                dont_filter=True,
            )
            return

        fpid = self._extract_fpid(response)
        if not fpid:
            self.logger.warning(f"Could not extract FPID from {response.url}")
            self.items_failed += 1
            return

        ld_json = self._parse_json_ld(response)
        initial_state = self._parse_initial_state(response)

        has_title = bool(
            (ld_json and ld_json.get("name"))
            or response.css("span.VU-ZEz::text").get()
            or response.css("h1 span::text").get()
        )
        has_price = bool(
            (ld_json and ld_json.get("offers"))
            or (initial_state and initial_state.get("ppd", {}).get("finalPrice"))
            or response.css("div._30jeq3::text").get()
            or response.css("div.Nx9bqj::text").get()
        )

        if has_title and has_price:
            yield from self._build_item(response, fpid, ld_json)
            return

        # Insufficient data — if plain HTTP, retry with camoufox
        if not is_camoufox:
            self.logger.info(
                f"Incomplete data for FPID {fpid} (title={has_title}, price={has_price}) "
                f"— promoting to camoufox"
            )
            yield scrapy.Request(
                response.url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "camoufox": True,
                    "camoufox_wait_ms": 5000,
                    "category_slug": response.meta.get("category_slug"),
                },
                dont_filter=True,
            )
            return

        # Already camoufox — extract whatever we can
        yield from self._build_item(response, fpid, ld_json)

    def _build_item(self, response, fpid: str, ld_json: dict | None):
        """Build and yield a ProductItem from HTML + JSON-LD + __INITIAL_STATE__."""
        initial_state = self._parse_initial_state(response)

        title = self._extract_title(response, ld_json)
        if not title:
            self.logger.warning(f"No title found for FPID {fpid}")
            self.items_failed += 1
            return

        raw_html_path = None
        if self._save_html:
            raw_html_path = self._save_raw_html(response, fpid)

        item = ProductItem()
        item["marketplace_slug"] = MARKETPLACE_SLUG
        item["external_id"] = fpid
        item["url"] = self._canonical_url(response.url, fpid)
        item["title"] = title
        item["brand"] = self._extract_brand(response, ld_json, initial_state)
        item["price"] = self._extract_price(response, ld_json, initial_state)
        item["mrp"] = self._extract_mrp(response, initial_state)
        item["images"] = self._extract_images(response, ld_json)
        item["rating"] = self._extract_rating(response, ld_json)
        item["review_count"] = self._extract_review_count(response, ld_json)
        item["specs"] = self._extract_specs(response)
        item["seller_name"] = self._extract_seller(response, ld_json, initial_state)
        item["seller_rating"] = self._extract_seller_rating(response)
        item["in_stock"] = self._extract_availability(response, ld_json, initial_state)
        item["fulfilled_by"] = self._extract_fulfilled_by(response)
        item["category_slug"] = response.meta.get("category_slug")
        item["about_bullets"] = self._extract_highlights(response)
        item["offer_details"] = self._extract_offers(response)
        item["raw_html_path"] = raw_html_path

        # Extended fields
        item["description"] = self._extract_description(response, ld_json)
        item["warranty"] = self._extract_warranty(response)
        item["delivery_info"] = self._extract_delivery_info(response)
        item["return_policy"] = self._extract_return_policy(response, initial_state)
        item["breadcrumbs"] = self._extract_breadcrumbs(response)
        item["variant_options"] = self._extract_variants(response, initial_state)
        specs = item["specs"]
        item["country_of_origin"] = self._extract_from_specs(
            specs, ["Country of Origin", "country of origin", "Country Of Origin"]
        )
        item["manufacturer"] = self._extract_from_specs(
            specs, ["Manufacturer", "manufacturer"]
        )
        item["model_number"] = self._extract_from_specs(
            specs, ["Model Number", "Model Name", "model number"]
        )
        item["weight"] = self._extract_from_specs(
            specs, ["Weight", "Net Weight", "weight", "Product Weight"]
        )
        item["dimensions"] = self._extract_from_specs(
            specs, ["Dimensions", "Product Dimensions", "dimensions"]
        )

        self.items_scraped += 1
        self._products_extracted += 1
        yield item

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_ld(response) -> dict | None:
        """Extract the first schema.org Product JSON-LD block from the page."""
        for script in response.css(
            'script[type="application/ld+json"]::text'
        ).getall():
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
    # __INITIAL_STATE__ extraction (Flipkart's Redux state)
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_initial_state(response) -> dict | None:
        """Extract product summary info (psi) from window.__INITIAL_STATE__.

        Uses json.JSONDecoder.raw_decode for robust parsing — handles
        the large embedded JSON blob even when followed by arbitrary JS.

        Returns a dict with keys like:
          ppd: {fsp, finalPrice, mrp, ...}
          bd: brand name
          pls: {sellerId, availabilityStatus, listingId, ...}
          swa: [{attributeValue, attributeName}, ...]  (variants)
          pi: {returnPolicy, isCODAvailable, isNoCostEmi}
        Or None if not found.
        """
        try:
            text = response.text
        except Exception:
            return None

        marker = "window.__INITIAL_STATE__"
        idx = text.find(marker)
        if idx < 0:
            return None

        eq_idx = text.find("=", idx)
        if eq_idx < 0:
            return None
        json_start = text.find("{", eq_idx)
        if json_start < 0:
            return None

        try:
            decoder = json.JSONDecoder()
            state, _ = decoder.raw_decode(text, json_start)
            psi = (
                state.get("pageDataV4", {})
                .get("page", {})
                .get("pageData", {})
                .get("pageContext", {})
                .get("fdpEventTracking", {})
                .get("events", {})
                .get("psi", {})
            )
            if psi:
                return psi
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        return None

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fpid(response) -> str | None:
        """Extract Flipkart Product ID (FPID) from URL."""
        match = FPID_RE.search(response.url)
        if match:
            return match.group(1)
        if "pid=" in response.url:
            pid = response.url.split("pid=")[-1].split("&")[0]
            if pid:
                return pid
        return None

    @staticmethod
    def _extract_title(response, ld_json: dict | None) -> str | None:
        """Extract product title."""
        if ld_json and ld_json.get("name"):
            return ld_json["name"].strip()
        for sel in [
            "span.VU-ZEz::text",
            "h1._6EBuvT span::text",
            "h1 span.B_NuCI::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        title = response.xpath(
            '//div[contains(@class,"aMaAEs") or contains(@class,"hGSR34")]'
            '//span[string-length(text()) > 10]/text()'
        ).get()
        return title.strip() if title else None

    @staticmethod
    def _extract_brand(
        response, ld_json: dict | None, initial_state: dict | None = None
    ) -> str | None:
        """Extract brand name from JSON-LD, __INITIAL_STATE__, or CSS fallback."""
        if ld_json:
            brand_obj = ld_json.get("brand")
            if isinstance(brand_obj, dict) and brand_obj.get("name"):
                return brand_obj["name"].strip()
            if isinstance(brand_obj, str) and brand_obj.strip():
                return brand_obj.strip()
        if initial_state and initial_state.get("bd"):
            return str(initial_state["bd"]).strip()
        breadcrumbs = response.css(
            "div._1MR4o5 a::text, div._2whKao a::text"
        ).getall()
        if len(breadcrumbs) >= 3:
            return breadcrumbs[2].strip()
        brand = response.xpath(
            '//td[text()="Brand" or text()="brand"]/following-sibling::td//text()'
        ).get()
        return brand.strip() if brand else None

    def _extract_price(
        self, response, ld_json: dict | None, initial_state: dict | None = None
    ) -> Decimal | None:
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

        if initial_state:
            ppd = initial_state.get("ppd", {})
            for key in ("finalPrice", "fsp"):
                raw = ppd.get(key)
                if raw is not None:
                    try:
                        rupees = Decimal(str(raw))
                        if rupees > 0:
                            return rupees * 100
                    except (InvalidOperation, ValueError):
                        pass

        for sel in [
            "div._30jeq3::text",
            "div._16Jk6d::text",
            "div.Nx9bqj::text",
            "div.hl05eU div.Nx9bqj::text",
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        price_text = response.xpath(
            '//div[contains(@class,"CEmi") or contains(@class,"_30jeq")]//text()'
        ).get()
        return self._parse_price_text(price_text)

    def _extract_mrp(
        self, response, initial_state: dict | None = None
    ) -> Decimal | None:
        """Extract MRP (strike-through price) in paisa."""
        if initial_state:
            ppd = initial_state.get("ppd", {})
            raw = ppd.get("mrp")
            if raw is not None:
                try:
                    rupees = Decimal(str(raw))
                    if rupees > 0:
                        return rupees * 100
                except (InvalidOperation, ValueError):
                    pass

        for sel in [
            "div._3I9_wc::text",
            "div._2p6lqe::text",
            "div.yRaY8j::text",
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        mrp_text = response.xpath(
            '//span[contains(@class,"_2p6lq") or contains(@style,"line-through")]//text()'
        ).get()
        return self._parse_price_text(mrp_text)

    def _extract_images(self, response, ld_json: dict | None) -> list[str]:
        """Extract all product image URLs (high resolution)."""
        images: list[str] = []

        if ld_json:
            img = ld_json.get("image")
            if isinstance(img, str) and img:
                images.append(self._high_res_image(img))
            elif isinstance(img, list):
                for i in img:
                    if isinstance(i, str) and i:
                        images.append(self._high_res_image(i))

        for img_url in response.css(
            'div._3kidJX img::attr(src), '
            'ul._1-n69S li img::attr(src), '
            'div._2E1FGS img::attr(src), '
            'div._1BweB8 img::attr(src)'
        ).getall():
            if "placeholder" in img_url:
                continue
            full = self._high_res_image(img_url)
            if full not in images:
                images.append(full)

        if not images:
            for img_url in response.css('img[src*="rukminim"]::attr(src)').getall():
                full = self._high_res_image(img_url)
                if full not in images:
                    images.append(full)

        return images[:10]

    @staticmethod
    def _extract_rating(response, ld_json: dict | None) -> Decimal | None:
        """Extract average star rating (0-5)."""
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                val = agg.get("ratingValue")
                if val is not None:
                    try:
                        return Decimal(str(val))
                    except InvalidOperation:
                        pass

        for sel in [
            "div._3LWZlK::text",
            "span._1lRcqv::text",
            "div.XQDdHH::text",
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
    def _extract_review_count(response, ld_json: dict | None) -> int | None:
        """Extract total number of ratings/reviews."""
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                for key in ("reviewCount", "ratingCount"):
                    val = agg.get(key)
                    if val is not None:
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            pass

        for sel in [
            "span._2_R_DZ::text",
            "span._13vcW::text",
            'div[class*="row"] span._2_R_DZ span::text',
        ]:
            for text in response.css(sel).getall():
                match = REVIEW_COUNT_RE.search(text)
                if match:
                    return int(match.group(1).replace(",", ""))

        count_text = response.xpath(
            '//*[contains(text(),"Rating") and contains(text(),"Review")]//text()'
        ).get()
        if count_text:
            match = REVIEW_COUNT_RE.search(count_text)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_seller(
        response, ld_json: dict | None, initial_state: dict | None = None
    ) -> str | None:
        """Extract seller name from JSON-LD, __INITIAL_STATE__, or CSS."""
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                seller = offers.get("seller")
                if isinstance(seller, dict) and seller.get("name"):
                    return seller["name"].strip()
            elif isinstance(offers, list):
                for offer in offers:
                    seller = offer.get("seller")
                    if isinstance(seller, dict) and seller.get("name"):
                        return seller["name"].strip()

        if initial_state:
            pls = initial_state.get("pls", {})
            seller_id = pls.get("sellerId")
            if seller_id:
                return seller_id

        for sel in [
            "#sellerName span span::text",
            "div._3enH3G span span::text",
            'div[id="sellerName"] a span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()

        return None

    @staticmethod
    def _extract_seller_rating(response) -> Decimal | None:
        """Extract seller rating (shown next to seller name)."""
        for sel in [
            "#sellerName div._3LWZlK::text",
            "div._3enH3G div._3LWZlK::text",
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
    def _extract_availability(
        response, ld_json: dict | None, initial_state: dict | None = None
    ) -> bool:
        """Determine if product is in stock."""
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                avail = offers.get("availability", "")
                if "InStock" in avail:
                    return True
                if "OutOfStock" in avail:
                    return False
            elif isinstance(offers, list):
                for offer in offers:
                    avail = offer.get("availability", "")
                    if "InStock" in avail:
                        return True

        if initial_state:
            pls = initial_state.get("pls", {})
            status = pls.get("availabilityStatus", "")
            if status == "IN_STOCK":
                return True
            if status in ("OUT_OF_STOCK", "UNAVAILABLE"):
                return False
            nb = initial_state.get("nb", {})
            if nb.get("isNonBuyable"):
                return False

        page_text = " ".join(
            response.css("div._16FRp0::text, div._1dVbu9::text").getall()
        ).lower()
        if (
            "sold out" in page_text
            or "coming soon" in page_text
            or "currently unavailable" in page_text
        ):
            return False

        return bool(response.css("div._30jeq3, div.Nx9bqj"))

    @staticmethod
    def _extract_fulfilled_by(response) -> str | None:
        """Extract fulfilment info — Flipkart Assured or seller-fulfilled."""
        assured = response.css(
            'img[src*="fa_62673a"]::attr(src), '
            'img[alt*="Assured"]::attr(alt), '
            'img[src*="fk-advantage"]::attr(src)'
        ).get()
        if assured:
            return "Flipkart"

        assured_text = response.xpath(
            '//*[contains(text(),"Flipkart Assured") or contains(text(),"F-Assured")]'
        ).get()
        if assured_text:
            return "Flipkart"

        return None

    @staticmethod
    def _extract_specs(response) -> dict[str, str]:
        """Extract technical specifications as key-value pairs."""
        specs: dict[str, str] = {}

        for row in response.css("div._14cfVK tr, table._14cfVK tr"):
            key = row.css("td:first-child::text").get("").strip()
            val = row.css("td:last-child li::text, td:last-child::text").get(
                ""
            ).strip()
            if key and val and key != val:
                specs[key] = val

        if not specs:
            for row in response.css(
                "div._3k-BhJ tr, table.G4BRas tr, table._3npaEj tr"
            ):
                key = row.css("td:first-child::text").get("").strip()
                val = row.css("td:last-child::text").get("").strip()
                if key and val and key != val:
                    specs[key] = val

        if not specs:
            spec_rows = response.xpath(
                '//div[.//text()="Specifications" or .//text()="SPECIFICATIONS"]'
                '//following-sibling::div//table//tr'
            )
            for row in spec_rows:
                cells = row.xpath(".//td//text()").getall()
                cells = [c.strip() for c in cells if c.strip()]
                if len(cells) >= 2:
                    specs[cells[0]] = cells[-1]

        return specs

    @staticmethod
    def _extract_highlights(response) -> list[str]:
        """Extract product highlights / key features bullet points."""
        bullets: list[str] = []

        for sel in [
            "div._2418kt li::text",
            "div.xFVion li::text",
            "div._3Rrcbo li::text",
        ]:
            items = response.css(sel).getall()
            if items:
                bullets = [b.strip() for b in items if b.strip()]
                break

        if not bullets:
            items = response.xpath(
                '//div[.//text()="Highlights" or .//text()="HIGHLIGHTS"]'
                '//following-sibling::div[1]//li//text()'
            ).getall()
            bullets = [b.strip() for b in items if b.strip()]

        return bullets

    @staticmethod
    def _extract_offers(response) -> list[dict]:
        """Extract bank offers, exchange offers, and EMI details."""
        offers: list[dict] = []

        offer_selectors = [
            "div._3Ht4Hy li",
            "div.DaXhCo li",
            "div._16eBzU li",
        ]

        offer_elements = []
        for sel in offer_selectors:
            offer_elements = response.css(sel)
            if offer_elements:
                break

        for elem in offer_elements:
            text_parts = elem.css("::text").getall()
            offer_text = " ".join(t.strip() for t in text_parts if t.strip())
            if not offer_text or len(offer_text) < 10:
                continue

            offer: dict = {"text": offer_text[:500]}
            lower = offer_text.lower()

            if "cashback" in lower:
                offer["type"] = "cashback"
            elif "no cost emi" in lower or "emi" in lower:
                offer["type"] = "emi"
            elif "exchange" in lower:
                offer["type"] = "exchange"
            elif "coupon" in lower:
                offer["type"] = "coupon"
            elif "bank" in lower or "card" in lower:
                offer["type"] = "bank_offer"
            elif "partner" in lower:
                offer["type"] = "partner_offer"
            else:
                offer["type"] = "other"

            offers.append(offer)

        if not offers:
            offer_items = response.xpath(
                '//div[.//text()="Available offers" or .//text()="Available Offers"]'
                '//following-sibling::div[1]//li'
            )
            for li in offer_items:
                text_parts = li.xpath(".//text()").getall()
                offer_text = " ".join(t.strip() for t in text_parts if t.strip())
                if offer_text and len(offer_text) >= 10:
                    lower = offer_text.lower()
                    offer_type = "other"
                    if "cashback" in lower:
                        offer_type = "cashback"
                    elif "emi" in lower:
                        offer_type = "emi"
                    elif "exchange" in lower:
                        offer_type = "exchange"
                    elif "bank" in lower or "card" in lower:
                        offer_type = "bank_offer"
                    offers.append({"text": offer_text[:500], "type": offer_type})

        return offers[:10]

    # ------------------------------------------------------------------
    # Extended field extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_description(response, ld_json: dict | None) -> str | None:
        """Extract product description from JSON-LD or page content."""
        if ld_json and ld_json.get("description"):
            return ld_json["description"].strip()[:5000]

        desc_parts = response.css(
            "div._1mXcCf p::text, div._1mXcCf::text"
        ).getall()
        if desc_parts:
            return " ".join(t.strip() for t in desc_parts if t.strip())[:5000]

        desc = response.xpath(
            '//div[.//text()="Description" or .//text()="DESCRIPTION"]'
            '//following-sibling::div[1]//text()'
        ).getall()
        if desc:
            return " ".join(t.strip() for t in desc if t.strip())[:5000]

        return None

    @staticmethod
    def _extract_warranty(response) -> str | None:
        """Extract warranty information from specs or dedicated section."""
        for row in response.css(
            "div._14cfVK tr, table._14cfVK tr, div._3k-BhJ tr"
        ):
            key = row.css("td:first-child::text").get("").strip().lower()
            if "warranty" in key:
                return row.css(
                    "td:last-child::text, td:last-child li::text"
                ).get("").strip()

        warranty = response.xpath(
            '//td[contains(translate(text(),"WARRANTY","warranty"),"warranty")]'
            '/following-sibling::td//text()'
        ).get()
        return warranty.strip() if warranty else None

    @staticmethod
    def _extract_delivery_info(response) -> str | None:
        """Extract delivery estimate."""
        for sel in [
            "div._3XINqE::text",
            "div._1TPvmH span::text",
            "div._2H87wv span::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip() and "deliver" in text.lower():
                return text.strip()
        return None

    @staticmethod
    def _extract_return_policy(
        response, initial_state: dict | None = None
    ) -> str | None:
        """Extract return policy text."""
        if initial_state:
            pi = initial_state.get("pi", {})
            rp = pi.get("returnPolicy")
            if rp and isinstance(rp, str):
                readable = rp.replace("_", " ").replace("action", "").strip()
                if readable:
                    return readable

        for sel in [
            "div._3n2dkM::text",
            "div._2TnXLR span::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip() and "return" in text.lower():
                return text.strip()

        ret = response.xpath(
            '//*[contains(text(),"Return Policy") or contains(text(),"day replacement")]//text()'
        ).get()
        return ret.strip() if ret else None

    @staticmethod
    def _extract_breadcrumbs(response) -> list[str]:
        """Extract navigation breadcrumb trail."""
        crumbs = response.css(
            "div._1MR4o5 a::text, div._2whKao a::text"
        ).getall()
        if crumbs:
            return [c.strip() for c in crumbs if c.strip()]
        crumbs = response.xpath(
            '//div[contains(@class,"breadcrumb")]//a//text()'
        ).getall()
        return [c.strip() for c in crumbs if c.strip()]

    @staticmethod
    def _extract_variants(
        response, initial_state: dict | None = None
    ) -> list[dict]:
        """Extract available variant options (color, RAM, storage, etc.)."""
        variants: list[dict] = []

        if initial_state:
            swa = initial_state.get("swa", [])
            if isinstance(swa, list):
                for attr in swa:
                    if isinstance(attr, dict):
                        name = attr.get("attributeName", "")
                        value = attr.get("attributeValue", "")
                        if name and value:
                            variants.append({"name": name, "value": value})
                if variants:
                    return variants[:30]

        for swatch in response.css("div._3V2wfe a, div._1fGeJ5 a, a._2GcJMG"):
            label = swatch.css("::attr(title)").get() or swatch.css("::text").get()
            href = swatch.css("::attr(href)").get()
            if label and label.strip():
                variant = {"value": label.strip()}
                if href and "/p/" in href:
                    variant["url"] = response.urljoin(href)
                variants.append(variant)

        return variants[:30]

    @staticmethod
    def _extract_from_specs(specs: dict, keys: list[str]) -> str | None:
        """Extract a specific value from specs dict by trying multiple key names."""
        if not specs:
            return None
        for key in keys:
            if key in specs:
                return specs[key]
            for spec_key, spec_val in specs.items():
                if spec_key.lower().strip() == key.lower().strip():
                    return spec_val
        return None

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract a category hint from a Flipkart search URL.

        Category resolution is now handled centrally by the pipeline via
        apps.products.category_mapper.resolve_canonical_category().
        This method returns None; the pipeline uses breadcrumbs + title.
        """
        return None

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _json_ld_price(offer: dict) -> Decimal | None:
        """Extract price in paisa from a JSON-LD Offer object."""
        raw = offer.get("price")
        if raw is None:
            return None
        try:
            rupees = Decimal(str(raw).replace(",", ""))
            if rupees <= 0:
                return None
            return rupees * 100
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_price_text(text: str | None) -> Decimal | None:
        """Parse price text like '₹24,999' to paisa Decimal."""
        if not text:
            return None
        text = text.strip()
        match = PRICE_RE.search(text)
        if not match:
            return None
        cleaned = match.group(0).replace(",", "")
        if not cleaned:
            return None
        try:
            rupees = Decimal(cleaned)
            if rupees <= 0:
                return None
            return rupees * 100
        except InvalidOperation:
            return None

    @staticmethod
    def _high_res_image(url: str) -> str:
        """Upgrade Flipkart image URL to high resolution."""
        return re.sub(r"/image/\d+/\d+/", "/image/832/832/", url)

    @staticmethod
    def _canonical_url(response_url: str, fpid: str) -> str:
        """Build a clean canonical URL for the product."""
        match = re.search(
            r"(https://www\.flipkart\.com/.+/p/" + re.escape(fpid) + r")",
            response_url,
        )
        if match:
            return match.group(1)
        return f"https://www.flipkart.com/product/p/{fpid}"

    def _save_raw_html(self, response, fpid: str) -> str | None:
        """Save response HTML to local filesystem for debugging."""
        try:
            raw_dir = Path(os.environ.get("SCRAPING_RAW_HTML_DIR", "data/raw_html"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"flipkart_{fpid}_{timestamp}.html"
            filepath = raw_dir / filename
            filepath.write_bytes(response.body)
            return str(filepath)
        except OSError as exc:
            self.logger.warning(f"Could not save raw HTML for {fpid}: {exc}")
            return None
