"""Meesho spider — camoufox-based scraper for Akamai Bot Manager bypass.

Architecture:
  Meesho is a Next.js CSR app. Akamai Bot Manager blocks ALL automated
  access — Playwright (headless/headed), curl_cffi, and even system Chrome
  via Playwright. Only camoufox (anti-detection Firefox) passes.

  Strategy:
    1. Search-based discovery: /search?q={term} via camoufox → product URLs
    2. Product detail pages: camoufox renders PDP → extract from
       __NEXT_DATA__.props.pageProps.initialState.product.details.data
    3. Fallback: DOM parsing for title, prices, images, rating

  Anti-bot: Akamai Bot Manager (aggressive — blocks even headed Chrome)
  Products called "catalogs" internally.

  All prices in RUPEES — converted to paisa (* 100) before yielding.

URL patterns:
  Search:   /search?q={query}  → 20 products per page
  Product:  /{slug}/p/{product-id}
"""

from __future__ import annotations

import json
import logging
import re
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

PRODUCT_ID_RE = re.compile(r"/p/(\w+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "meesho"

# ---------------------------------------------------------------------------
# Category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Fashion — Women
    "sarees": "womens-fashion",
    "kurtis": "womens-fashion",
    "women-kurtis": "womens-fashion",
    "lehengas": "womens-fashion",
    "tops-ladies": "womens-fashion",
    "dresses-women": "womens-fashion",
    "dupattas": "womens-fashion",
    "blouses": "womens-fashion",
    "gowns-women": "womens-fashion",
    "night-suits-women": "womens-fashion",
    # Fashion — Men
    "men-fashion": "mens-fashion",
    "men-t-shirts": "mens-fashion",
    "shirts-men": "mens-fashion",
    "jeans-men": "mens-fashion",
    "men-kurtas": "mens-fashion",
    "track-pants-men": "mens-fashion",
    # Kids
    "kids-clothing": "kids-fashion",
    "girls-clothing": "kids-fashion",
    "boys-clothes": "kids-fashion",
    # Footwear
    "footwear": "footwear",
    "men-footwear": "footwear",
    "women-footwear": "footwear",
    "sports-shoes-men": "footwear",
    # Home
    "bedsheets": "home-decor",
    "home-decor": "home-decor",
    "curtains-sheers": "home-decor",
    "cushion-covers": "home-decor",
    # Beauty
    "beauty-products": "beauty",
    "skincare": "skincare",
    "hair-care": "hair-care",
    # Accessories
    "jewellery": "jewellery",
    "watches": "watches",
    "bags": "accessories",
    "sunglasses-women": "accessories",
    "sunglasses-men": "accessories",
    # Electronics
    "electronic-accessories": "electronics",
    "smartphones": "smartphones",
    "headphones": "audio",
    "speakers": "audio",
}

# Search queries for discovery — each maps to a search term and whydud category.
SEED_SEARCH_QUERIES: list[tuple[str, str | None]] = [
    # Women's Fashion (Meesho's biggest segment)
    ("sarees", "womens-fashion"),
    ("kurtis", "womens-fashion"),
    ("lehengas", "womens-fashion"),
    ("women tops", "womens-fashion"),
    ("women dresses", "womens-fashion"),
    # Men's Fashion
    ("men tshirts", "mens-fashion"),
    ("men shirts", "mens-fashion"),
    ("men jeans", "mens-fashion"),
    # Kids
    ("kids clothing", "kids-fashion"),
    # Footwear
    ("men footwear", "footwear"),
    ("women footwear", "footwear"),
    # Home
    ("bedsheets", "home-decor"),
    ("home decor", "home-decor"),
    # Beauty & Accessories
    ("jewellery", "jewellery"),
    ("beauty products", "beauty"),
    # Electronics
    ("mobile accessories", "electronics"),
    ("headphones", "audio"),
]

QUICK_MODE_QUERIES = 4

# ---------------------------------------------------------------------------
# Camoufox downloader middleware
# ---------------------------------------------------------------------------


class MeeshoCamoufoxMiddleware:
    """Scrapy downloader middleware using camoufox (anti-detection Firefox).

    Camoufox bypasses Akamai Bot Manager which blocks Playwright, curl_cffi,
    and even headed Chrome with stealth patches. It achieves this by using a
    patched Firefox binary with realistic fingerprints.

    Runs camoufox sync API in a dedicated thread (via Twisted's deferToThread)
    because:
      - Sync API can't run in Scrapy's asyncio event loop (detects it)
      - Async API needs ProactorEventLoop on Windows (Scrapy uses Selector)

    The middleware manages a single browser context that persists across
    requests for cookie/session continuity.
    """

    def __init__(self) -> None:
        self._context = None
        self._camoufox_cm = None
        self._request_count = 0
        self._lock = None  # Threading lock for browser access

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
        # subprocess creation. Scrapy forces SelectorEventLoop, but we can
        # set the policy here so the sync API's internal event loop uses
        # Proactor. This is safe because Scrapy already created its loop.
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        from camoufox.sync_api import Camoufox

        self._camoufox_cm = Camoufox(headless=True)
        self._context = self._camoufox_cm.__enter__()
        logger.info("Camoufox browser started for Meesho spider (thread pool)")

    def _fetch_page(self, url: str, wait_ms: int) -> tuple[int, bytes]:
        """Render a page with camoufox (runs in worker thread)."""
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
        """Intercept requests to meesho.com and render via camoufox."""
        if request.meta.get("skip_camoufox"):
            return None
        if "meesho.com" not in request.url:
            return None

        self._request_count += 1
        wait_ms = request.meta.get("camoufox_wait_ms", 10000)

        try:
            # Run the sync camoufox code in a thread pool worker
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
                self._camoufox_cm.__exit__(None, None, None)
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


class MeeshoSpider(BaseWhydudSpider):
    """Scrapes Meesho.com — budget marketplace with aggressive Akamai.

    Uses camoufox (anti-detection Firefox) instead of Playwright.
    Two-phase: search pages for discovery → product pages for detail.

    Spider arguments:
      job_id  — UUID of a ScraperJob row.
      urls    — comma-separated product or search URLs to scrape directly.
      max_pages — max search result pages per query (default 1).
    """

    name = "meesho"
    allowed_domains = ["meesho.com", "www.meesho.com"]

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
            "apps.scraping.spiders.meesho_spider.MeeshoCamoufoxMiddleware": 100,
            "apps.scraping.middlewares.BackoffRetryMiddleware": 350,
        },
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        job_id: str | None = None,
        urls: str | None = None,
        max_pages: str | None = None,
        *args,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.job_id = job_id
        self._override_urls: list[str] = (
            [u.strip() for u in urls.split(",") if u.strip()] if urls else []
        )
        self._max_pages: int = int(max_pages) if max_pages else 1

        # Stats
        self._search_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._state_extractions: int = 0
        self._dom_extractions: int = 0

    def closed(self, reason: str) -> None:
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Meesho spider finished ({reason}): "
            f"searches={self._search_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"state={self._state_extractions}, dom={self._dom_extractions}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit requests — search pages for discovery or direct URLs."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob

                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        if self._override_urls:
            for url in self._override_urls:
                if "/p/" in url:
                    # Direct product URL
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
                    # Search or category URL
                    yield scrapy.Request(
                        url,
                        callback=self.parse_search_page,
                        errback=self.handle_error,
                        meta={
                            "category_slug": self._resolve_category_from_url(url),
                            "camoufox_wait_ms": 12000,
                            "page_num": 1,
                        },
                        dont_filter=True,
                    )
        else:
            queries = SEED_SEARCH_QUERIES
            if self._max_pages <= 1:
                queries = queries[:QUICK_MODE_QUERIES]

            for term, category_slug in queries:
                url = f"https://www.meesho.com/search?q={term.replace(' ', '+')}"
                yield scrapy.Request(
                    url,
                    callback=self.parse_search_page,
                    errback=self.handle_error,
                    meta={
                        "category_slug": category_slug,
                        "search_term": term,
                        "camoufox_wait_ms": 12000,
                        "page_num": 1,
                    },
                    dont_filter=True,
                )

        count = len(self._override_urls) or len(queries)
        self.logger.info(f"Queued {count} requests (camoufox)")

    # ------------------------------------------------------------------
    # Phase 1: Search / listing pages
    # ------------------------------------------------------------------

    def parse_search_page(self, response):
        """Extract product links from search results page."""
        self._search_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on search {response.url}")
            return

        category_slug = response.meta.get("category_slug")
        page_num = response.meta.get("page_num", 1)

        # Extract product URLs from DOM links
        product_urls = set()
        for href in response.css("a[href*='/p/']::attr(href)").getall():
            full = response.urljoin(href)
            if "/p/" in full:
                product_urls.add(full)

        if product_urls:
            self.logger.info(
                f"Found {len(product_urls)} products on {response.url}"
            )
            for prod_url in product_urls:
                yield scrapy.Request(
                    prod_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    meta={
                        "category_slug": category_slug,
                        "camoufox_wait_ms": 10000,
                    },
                )
        else:
            self.logger.warning(f"No products found on {response.url}")
            return

        # Pagination — Meesho search uses ?page=N
        if page_num < self._max_pages:
            next_page = page_num + 1
            base = response.url.split("&page=")[0].split("?page=")[0]
            sep = "&" if "?" in base else "?"
            next_url = f"{base}{sep}page={next_page}"

            yield scrapy.Request(
                next_url,
                callback=self.parse_search_page,
                errback=self.handle_error,
                meta={
                    "category_slug": category_slug,
                    "search_term": response.meta.get("search_term"),
                    "camoufox_wait_ms": 12000,
                    "page_num": next_page,
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

        id_match = PRODUCT_ID_RE.search(response.url)
        external_id = id_match.group(1) if id_match else None

        # Strategy 1: __NEXT_DATA__ → product.details.data (richest source)
        state = self._extract_next_data(response)
        if state:
            product_state = (
                state.get("props", {})
                .get("pageProps", {})
                .get("initialState", {})
                .get("product", {})
            )
            details = product_state.get("details", {}).get("data")
            if details and details.get("name"):
                item = self._build_from_state(
                    details, response.url, category_slug, external_id
                )
                if item:
                    self._state_extractions += 1
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: DOM parsing fallback
        item = self._build_from_dom(response, category_slug, external_id)
        if item:
            self._dom_extractions += 1
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        self.logger.warning(f"Could not extract from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # State extraction
    # ------------------------------------------------------------------

    def _extract_next_data(self, response) -> dict | None:
        """Extract __NEXT_DATA__ JSON from rendered page."""
        script = response.css('script#__NEXT_DATA__::text').get()
        if script:
            try:
                return json.loads(script)
            except (json.JSONDecodeError, ValueError):
                pass

        # Regex fallback
        match = re.search(
            r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>',
            response.text,
            re.DOTALL,
        )
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                pass
        return None

    # ------------------------------------------------------------------
    # Item builders
    # ------------------------------------------------------------------

    def _build_from_state(
        self,
        data: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from __NEXT_DATA__ product.details.data."""
        name = (data.get("name") or "").strip()
        if not name:
            return None

        pid = external_id or data.get("product_id") or data.get("handle") or ""
        pid = str(pid)
        if not pid:
            return None

        # Prices — in rupees, convert to paisa
        selling_price = self._to_paisa(data.get("price"))

        mrp_details = data.get("mrp_details") or {}
        mrp = self._to_paisa(mrp_details.get("mrp"))

        # If no top-level price, check first supplier
        suppliers = data.get("suppliers") or []
        first_supplier = suppliers[0] if suppliers else {}
        if selling_price is None and first_supplier:
            selling_price = self._to_paisa(first_supplier.get("price"))

        # Images
        images = data.get("images") or []

        # Rating / reviews
        review_summary = (data.get("review_summary") or {}).get("data") or {}
        rating = None
        review_count = None
        rating_count = None

        avg_rating = review_summary.get("average_rating")
        if avg_rating is not None:
            try:
                rating = Decimal(str(avg_rating))
            except (InvalidOperation, ValueError):
                pass

        rc = review_summary.get("review_count")
        if rc is not None:
            try:
                review_count = int(rc)
            except (ValueError, TypeError):
                pass

        rc2 = review_summary.get("rating_count")
        if rc2 is not None:
            try:
                rating_count = int(rc2)
            except (ValueError, TypeError):
                pass

        # Supplier / seller
        supplier_name = data.get("supplier_name") or (
            first_supplier.get("name") if first_supplier else None
        )
        seller_rating = None
        if first_supplier.get("average_rating"):
            try:
                seller_rating = Decimal(str(first_supplier["average_rating"]))
            except (InvalidOperation, ValueError):
                pass

        # Description and specs
        description = data.get("description") or ""
        specs = self._parse_specs_from_description(description)

        product_details = data.get("product_details") or {}
        highlights = product_details.get("product_highlights") or {}
        about_bullets = []
        for item_group in highlights.get("items") or []:
            title = item_group.get("title", "")
            value = item_group.get("value", "")
            if title and value:
                about_bullets.append(f"{title}: {value}")
                specs[title] = value

        # Breadcrumbs
        breadcrumbs = []
        for crumb in data.get("breadcrumb") or []:
            title = crumb.get("title")
            if title:
                breadcrumbs.append(title)

        # Variants
        variations = data.get("variations") or []

        # Shipping / delivery
        shipping = data.get("shipping") or {}
        delivery_info = None
        est = shipping.get("estimated_delivery") or {}
        if est.get("date"):
            delivery_info = f"{est.get('title', 'Delivery by ')}{est['date']}"
        if shipping.get("show_free_delivery"):
            delivery_info = f"Free Delivery — {delivery_info}" if delivery_info else "Free Delivery"

        # Return policy from value_props
        return_policy = None
        for vp in first_supplier.get("value_props") or []:
            if "return" in (vp.get("name") or "").lower():
                policy_data = vp.get("data") or {}
                return_policy = policy_data.get("message")
                break

        # Country of origin — often in description
        country = None
        co_match = re.search(r"Country of Origin:\s*(\w[\w\s]*)", description)
        if co_match:
            country = co_match.group(1).strip()

        # Canonical URL
        canonical = (data.get("meta_info") or {}).get("canonical_url") or url

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=canonical,
            title=name,
            brand=None,  # Meesho doesn't have brand-level data
            price=selling_price,
            mrp=mrp,
            images=[img for img in images if img],
            rating=rating,
            review_count=review_count or rating_count,
            specs=specs,
            seller_name=supplier_name or "Meesho",
            seller_rating=seller_rating,
            in_stock=data.get("in_stock", True),
            fulfilled_by="Meesho",
            category_slug=category_slug or self._resolve_category_from_breadcrumbs(breadcrumbs),
            about_bullets=about_bullets,
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=None,
            delivery_info=delivery_info,
            return_policy=return_policy,
            breadcrumbs=breadcrumbs,
            variant_options=variations,
            country_of_origin=country,
            manufacturer=supplier_name,
            model_number=None,
            weight=None,
            dimensions=None,
        )

    def _build_from_dom(
        self,
        response,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Fallback: extract product data from rendered DOM."""
        title = response.css("h1::text").get()
        if not title:
            title = response.css("h1 ::text").get()
        if not title or not title.strip():
            return None
        title = title.strip()

        pid = external_id or ""
        if not pid:
            return None

        # Prices from DOM text — look for ₹ symbols
        price_texts = response.css("*::text").re(r"₹\s*([\d,]+)")
        selling_price = None
        mrp = None
        if price_texts:
            selling_price = self._to_paisa(price_texts[0].replace(",", ""))
            if len(price_texts) > 1:
                # Second price is often the MRP (crossed out)
                mrp_val = self._to_paisa(price_texts[1].replace(",", ""))
                if mrp_val and selling_price and mrp_val > selling_price:
                    mrp = mrp_val

        # Images
        images = []
        for src in response.css('img[src*="images.meesho.com"]::attr(src)').getall():
            # Get high-res version
            clean = re.sub(r"\?width=\d+", "", src)
            clean = clean.replace("_128.", "_512.").replace("_64.", "_512.")
            if clean not in images:
                images.append(clean)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=response.url,
            title=title,
            brand=None,
            price=selling_price,
            mrp=mrp,
            images=images[:8],
            rating=None,
            review_count=None,
            specs={},
            seller_name="Meesho",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Meesho",
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

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _to_paisa(self, value) -> Decimal | None:
        """Convert a rupee value (int, float, str) to Decimal paisa."""
        if value is None:
            return None
        try:
            val_str = str(value).replace(",", "").replace("₹", "").strip()
            match = PRICE_RE.search(val_str)
            if not match:
                return None
            rupees = Decimal(match.group().replace(",", ""))
            return rupees * 100 if rupees > 0 else None
        except (InvalidOperation, ValueError):
            return None

    def _is_blocked(self, response) -> bool:
        """Detect Akamai block or empty page."""
        if response.status in (403, 429, 503):
            return True
        if len(response.text) < 1000:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        return "access denied" in title or "blocked" in title

    def _parse_specs_from_description(self, desc: str) -> dict:
        """Parse key-value specs from Meesho description text."""
        specs = {}
        for line in desc.split("\n"):
            line = line.strip()
            if ":" in line:
                key, _, val = line.partition(":")
                key = key.strip()
                val = val.strip()
                if key and val and len(key) < 50:
                    specs[key] = val
        return specs

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path."""
        path = url.split("meesho.com/")[-1].split("/")[0].split("?")[0].lower()
        if path in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[path]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in url.lower():
                return slug
        return None

    def _resolve_category_from_breadcrumbs(self, breadcrumbs: list[str]) -> str | None:
        """Infer category from breadcrumb titles."""
        for crumb in breadcrumbs:
            crumb_lower = crumb.lower().replace(" ", "-")
            for keyword, slug in KEYWORD_CATEGORY_MAP.items():
                if keyword in crumb_lower:
                    return slug
        return None
