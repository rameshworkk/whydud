"""Nykaa spider — HTTP-only scraper for beauty & personal care products.

Architecture:
  Phase 1 (Listing): HTTP GET to category pages, extract products from
    window.__PRELOADED_STATE__ → categoryListing.listingData.products.
    Pagination via ?page_no=N query param. ~20 products per page.
  Phase 2 (Detail): HTTP GET to product pages, extract structured data
    from __PRELOADED_STATE__ → productPage.product. Falls back to
    JSON-LD Product schema.

  NO Playwright — HTTP only. Uses curl_cffi with Chrome/120 TLS
  impersonation to bypass Akamai Bot Manager's JA3 fingerprinting.
  Python's standard ssl/urllib3 TLS fingerprint is blocked (403).

  Prices on Nykaa are in RUPEES (not paisa). Spider converts to paisa
  (* 100) before yielding.

CRITICAL: Standard Python HTTP clients (requests, urllib3, Twisted) are
blocked by Akamai because of their TLS (JA3) fingerprint. Must use
curl_cffi with `impersonate='chrome120'` for browser-like TLS handshake.

URL patterns:
  Category: /{category-path}/c/{numeric-id}?page_no={n}
  Product:  /{product-slug}/p/{product-id}

Data sources (priority order):
  1. window.__PRELOADED_STATE__ (Redux store) — richest
  2. JSON-LD <script type="application/ld+json"> — clean structured data
  3. window.dataLayer — analytics summary (listing pages only)
"""
import json
import logging
import random
import re
import time
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

MARKETPLACE_SLUG = "nykaa"

PRODUCT_ID_RE = re.compile(r"/p/(\d+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

# Chrome/120 User-Agent — Nykaa's Akamai blocks newer Chrome versions.
NYKAA_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Required headers for Akamai bypass — applied by CurlCffiMiddleware
NYKAA_HEADERS = {
    "User-Agent": NYKAA_USER_AGENT,
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-IN,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


# ===================================================================
# CurlCffi downloader middleware — Chrome TLS impersonation
# ===================================================================


class CurlCffiDownloaderMiddleware:
    """Scrapy downloader middleware that uses curl_cffi for requests.

    Akamai Bot Manager fingerprints TLS handshakes (JA3/JA4).
    Python's ssl module and Twisted have a distinct fingerprint that's
    blocked (403 on every request). curl_cffi wraps libcurl and can
    impersonate a real Chrome browser's TLS handshake.

    This middleware intercepts all requests to nykaa.com and makes them
    via curl_cffi with `impersonate='chrome120'`, then converts the
    response back into a Scrapy HtmlResponse.
    """

    def __init__(self) -> None:
        from curl_cffi import requests as curl_requests  # noqa: F811
        self._session = curl_requests.Session(impersonate="chrome120")
        self._request_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(
            middleware.spider_closed, signal=signals.spider_closed,
        )
        return middleware

    def spider_closed(self) -> None:
        """Close the curl_cffi session on spider shutdown."""
        try:
            self._session.close()
        except Exception:
            pass

    def process_request(self, request, spider):
        """Intercept request and fetch via curl_cffi."""
        # Only handle non-Playwright requests to nykaa.com
        if request.meta.get("playwright"):
            return None
        if "nykaa.com" not in request.url:
            return None

        self._request_count += 1

        try:
            resp = self._session.get(
                request.url,
                headers=NYKAA_HEADERS,
                timeout=60,
                allow_redirects=True,
            )

            return HtmlResponse(
                url=str(resp.url),
                status=resp.status_code,
                headers=dict(resp.headers),
                body=resp.content,
                request=request,
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning(f"curl_cffi request failed for {request.url}: {exc}")
            # Fall through to default handler
            return None


# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Skincare
    "skin": "skincare",
    "moisturizers": "skincare",
    "moisturiser": "skincare",
    "sunscreen": "skincare",
    "face-wash": "skincare",
    "face wash": "skincare",
    "cleanser": "skincare",
    "cleansers": "skincare",
    "serum": "skincare",
    "serums": "skincare",
    "face-masks": "skincare",
    "masks": "skincare",
    "toner": "skincare",
    "toners": "skincare",
    "eye-cream": "skincare",
    "eye-care": "skincare",
    "lip-care": "skincare",
    "lip-balm": "skincare",
    "sun-care": "skincare",
    "night-cream": "skincare",
    "scrubs": "skincare",
    # Makeup
    "makeup": "makeup",
    "foundation": "makeup",
    "face-foundation": "makeup",
    "concealer": "makeup",
    "face-concealer": "makeup",
    "lipstick": "makeup",
    "lip-color": "makeup",
    "lip-gloss": "makeup",
    "lip-stain": "makeup",
    "mascara": "makeup",
    "eye-mascara": "makeup",
    "eyeliner": "makeup",
    "eyeshadow": "makeup",
    "blush": "makeup",
    "compact": "makeup",
    "kajal": "makeup",
    "primer": "makeup",
    "nail-polish": "makeup",
    "nail polish": "makeup",
    "setting-spray": "makeup",
    "bb-cc-cream": "makeup",
    "face-illuminator": "makeup",
    "tools-brushes": "makeup",
    # Hair Care
    "hair": "hair-care",
    "hair-care": "hair-care",
    "shampoo": "hair-care",
    "conditioner": "hair-care",
    "hair-oil": "hair-care",
    "hair oil": "hair-care",
    "hair-serum": "hair-care",
    "hair serum": "hair-care",
    "hair-mask": "hair-care",
    "hair-creams": "hair-care",
    "hair-color": "hair-care",
    "hair color": "hair-care",
    # Bath & Body
    "bath-body": "bath-body",
    "bath-and-body": "bath-body",
    "bath-and-shower": "bath-body",
    "body-lotion": "bath-body",
    "body lotion": "bath-body",
    "shower-gel": "bath-body",
    "shower-gels": "bath-body",
    "body-wash": "bath-body",
    "deodorant": "bath-body",
    # Fragrance
    "perfume": "fragrance",
    "perfumes": "fragrance",
    "fragrance": "fragrance",
    "body-mist": "fragrance",
    # Men's Grooming
    "men": "grooming",
    "mens-grooming": "grooming",
    "beard": "grooming",
    "shaving": "grooming",
    "shaving-hair-removal": "grooming",
    "after-shave": "grooming",
    # Natural & Wellness
    "natural": "wellness",
    "wellness": "wellness",
    "health-and-wellness": "wellness",
    "supplements": "wellness",
    "vitamins": "wellness",
    # Appliances
    "appliances": "beauty-appliances",
    "personal-care-appliances": "beauty-appliances",
    "hair-dryer": "beauty-appliances",
    "straightener": "beauty-appliances",
    "trimmer": "beauty-appliances",
    "hair-removal-tools": "beauty-appliances",
    # Luxe
    "luxe": "luxury-beauty",
}

# ---------------------------------------------------------------------------
# Seed category URLs — verified working with correct IDs
# Format: (url, whydud_category_slug, max_pages)
#
# Category IDs discovered from nykaa.com homepage on 2026-03-03.
# Nykaa uses numeric IDs that don't map to path; path is SEO-only.
# ---------------------------------------------------------------------------

SEED_CATEGORY_URLS: list[tuple[str, str, int]] = [
    # ── Makeup (top-level: c/12, ~11K products) ──────────────────────────
    ("https://www.nykaa.com/makeup/face/face-foundation/c/228", "makeup", 5),
    ("https://www.nykaa.com/makeup/lips/lipstick/c/249", "makeup", 5),
    ("https://www.nykaa.com/makeup/lips/lip-gloss/c/250", "makeup", 3),
    ("https://www.nykaa.com/makeup/eyes/eyeliner/c/240", "makeup", 5),
    ("https://www.nykaa.com/makeup/eyes/eye-mascara/c/241", "makeup", 3),
    ("https://www.nykaa.com/makeup/eyes/eyeshadow/c/242", "makeup", 3),
    ("https://www.nykaa.com/makeup/face/face-concealer/c/234", "makeup", 3),
    ("https://www.nykaa.com/makeup/face/bb-cc-cream/c/232", "makeup", 3),
    # ── Skincare ─────────────────────────────────────────────────────────
    ("https://www.nykaa.com/skin/cleansers/face-wash/c/8379", "skincare", 5),
    ("https://www.nykaa.com/skin/sun-care/face-sunscreen/c/8429", "skincare", 5),
    ("https://www.nykaa.com/skin/moisturizers/night-cream/c/8395", "skincare", 3),
    ("https://www.nykaa.com/skin/masks/masks-peels/c/8400", "skincare", 3),
    ("https://www.nykaa.com/skin/toners-mists/c/8391", "skincare", 3),
    ("https://www.nykaa.com/skin/eye-care/under-eye-cream-serums/c/8403", "skincare", 3),
    ("https://www.nykaa.com/skin/lip-care/lip-balm/c/8409", "skincare", 3),
    # ── Hair Care ────────────────────────────────────────────────────────
    ("https://www.nykaa.com/hair-care/hair/hair-serum/c/320", "hair-care", 3),
    ("https://www.nykaa.com/hair-care/hair/hair-creams-masks/c/2041", "hair-care", 3),
    # ── Fragrance ────────────────────────────────────────────────────────
    ("https://www.nykaa.com/fragrance/women/perfumes-edt-edp/c/962", "fragrance", 5),
    ("https://www.nykaa.com/fragrance/women/body-mist-spray/c/970", "fragrance", 3),
    # ── Bath & Body ──────────────────────────────────────────────────────
    ("https://www.nykaa.com/bath-body/bath-and-shower/shower-gels-body-wash/c/368", "bath-body", 3),
    # ── Luxe ─────────────────────────────────────────────────────────────
    ("https://www.nykaa.com/luxe/brands/mac/foundation/c/4054", "luxury-beauty", 3),
]

MAX_LISTING_PAGES = 5


class NykaaSpider(BaseWhydudSpider):
    """Scrapes Nykaa.com beauty & personal care marketplace.

    HTTP-only spider — NO Playwright. Bypasses Akamai Bot Manager using
    specific Chrome/120 headers (Sec-Fetch-*, sec-ch-ua). Newer Chrome
    versions (131+) are blocked by Akamai.

    Data extraction from window.__PRELOADED_STATE__ (Redux store) with
    JSON-LD Product schema as fallback.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "nykaa"
    allowed_domains = ["nykaa.com", "www.nykaa.com"]

    QUICK_MODE_CATEGORIES = 4

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
        # CurlCffi middleware intercepts HTTP requests and uses Chrome
        # TLS impersonation to bypass Akamai JA3 fingerprinting.
        # Priority 100 = runs before all other downloader middlewares.
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.spiders.nykaa_spider.CurlCffiDownloaderMiddleware": 100,
            "apps.scraping.middlewares.BackoffRetryMiddleware": 350,
            "apps.scraping.middlewares.PlaywrightProxyMiddleware": 400,
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

        # Dedup — track seen product IDs
        self._seen_ids: set[str] = set()

        # Pagination tracking per base URL
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._products_extracted: int = 0
        self._duplicates_skipped: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._products_extracted / total * 100) if total > 0 else 0
        self.logger.info(
            f"Nykaa spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_pages={self._product_pages_scraped}, "
            f"products_ok={self._products_extracted} ({rate:.0f}%), "
            f"duplicates_skipped={self._duplicates_skipped}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Header override — Akamai bypass requires EXACT Chrome/120 headers
    # ------------------------------------------------------------------

    def _make_headers(self) -> dict[str, str]:
        """Return Nykaa-specific headers.

        NOTE: These headers are passed to Scrapy Request objects for
        compatibility, but the actual HTTP request is made by the
        CurlCffiDownloaderMiddleware using NYKAA_HEADERS with Chrome
        TLS impersonation. The Scrapy headers are used as fallback.
        """
        return dict(NYKAA_HEADERS)

    # ------------------------------------------------------------------
    # start_requests — HTTP only, no Playwright
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit HTTP requests for category listing pages."""
        url_triples = self._load_urls()
        random.shuffle(url_triples)

        for url, cat_slug, max_pg in url_triples:
            base = url.split("?")[0]
            self._max_pages_map[base] = max_pg

            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": cat_slug,
                    "playwright": False,
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_triples)} categories (HTTP-only)")

    def _load_urls(self) -> list[tuple[str, str, int]]:
        """Resolve the (url, category_slug, max_pages) list to crawl."""
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._category_urls:
            return [
                (u, self._resolve_category_from_url(u) or "", fallback)
                for u in self._category_urls
            ]

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, "
                    f"marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(
                    f"Could not load ScraperJob {self.job_id}: {exc}"
                )

        if self._max_pages_override is not None:
            if self._max_pages_override <= 2:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_CATEGORIES} "
                    f"categories (max_pages={self._max_pages_override})"
                )
                return [
                    (url, cat, self._max_pages_override)
                    for url, cat, _ in SEED_CATEGORY_URLS[
                        : self.QUICK_MODE_CATEGORIES
                    ]
                ]
            return [
                (url, cat, self._max_pages_override)
                for url, cat, _ in SEED_CATEGORY_URLS
            ]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path."""
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None

    def _extract_preloaded_state(self, response) -> dict | None:
        """Extract window.__PRELOADED_STATE__ JSON from page source.

        Uses json.JSONDecoder.raw_decode() for robustness against
        malformed/truncated JSON from SSR pages.
        """
        text = response.text
        marker = "window.__PRELOADED_STATE__"
        idx = text.find(marker)
        if idx == -1:
            return None

        # Find the opening brace
        brace_idx = text.find("{", idx)
        if brace_idx == -1:
            return None

        try:
            decoder = json.JSONDecoder()
            state, _ = decoder.raw_decode(text, brace_idx)
            return state
        except (json.JSONDecodeError, ValueError):
            # Fallback: try regex extraction
            match = re.search(
                r"window\.__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;\s*</script>",
                text,
                re.DOTALL,
            )
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, ValueError):
                    pass
            self.logger.warning(
                f"Failed to parse __PRELOADED_STATE__ on {response.url}"
            )
            return None

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value (rupees) to Decimal in paisa."""
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
            return rupees * 100  # convert to paisa
        except (InvalidOperation, ValueError):
            return None

    def _is_blocked(self, response) -> bool:
        """Detect if Akamai served a block/challenge page."""
        if response.status in (403, 429):
            return True
        # Akamai challenge pages are typically small HTML
        if len(response.text) < 500 and "Access Denied" in response.text:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Category listing pages (HTTP only)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from category listing page.

        Primary: categoryListing.listingData.products from __PRELOADED_STATE__
        Backup: product links from HTML (href="/...slug.../p/{id}")
        """
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(
                f"Blocked ({response.status}) on listing {response.url} — "
                f"headers may have changed"
            )
            return

        if response.status == 404:
            self.logger.warning(
                f"404 on category {response.url} — category ID may be stale"
            )
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: Extract from __PRELOADED_STATE__
        state = self._extract_preloaded_state(response)
        products = []
        total_found = 0
        stop_further = False

        if state:
            listing_data = (
                state.get("categoryListing", {}).get("listingData", {})
            )
            products = listing_data.get("products", [])
            total_found = listing_data.get("totalFound", 0)
            stop_further = listing_data.get("stopFurtherCall", False)

            if not products:
                # Try alternate paths in Redux state
                for key in ("category", "search", "searchListingPage"):
                    section = state.get(key, {})
                    if isinstance(section, dict):
                        ld = section.get("listingData", section)
                        prod_list = ld.get("products", [])
                        if prod_list:
                            products = prod_list
                            total_found = ld.get("totalFound", 0)
                            break

        product_count = 0

        if products:
            self.logger.info(
                f"Found {len(products)} products (state, "
                f"total={total_found}) on {response.url}"
            )
            for prod in products:
                prod_id = str(
                    prod.get("id")
                    or prod.get("productId")
                    or prod.get("childId")
                    or ""
                )
                if not prod_id:
                    continue

                # Dedup
                if prod_id in self._seen_ids:
                    self._duplicates_skipped += 1
                    continue
                self._seen_ids.add(prod_id)

                slug = prod.get("slug", "")
                if slug:
                    if slug.startswith("/"):
                        product_url = f"https://www.nykaa.com{slug}"
                    elif slug.startswith("http"):
                        product_url = slug
                    else:
                        product_url = f"https://www.nykaa.com/{slug}"
                else:
                    # Build URL from name + id
                    product_url = f"https://www.nykaa.com/p/{prod_id}"

                product_count += 1

                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "category_slug": category_slug,
                        "listing_data": prod,
                        "playwright": False,
                    },
                )
        else:
            # Strategy 2: HTML product links
            links = response.css("a[href*='/p/']::attr(href)").getall()
            seen_urls: set[str] = set()
            for href in links:
                full_url = response.urljoin(href)
                if full_url in seen_urls or "/p/" not in full_url:
                    continue
                seen_urls.add(full_url)

                # Extract product ID for dedup
                id_match = PRODUCT_ID_RE.search(full_url)
                if id_match:
                    pid = id_match.group(1)
                    if pid in self._seen_ids:
                        self._duplicates_skipped += 1
                        continue
                    self._seen_ids.add(pid)

                product_count += 1
                yield scrapy.Request(
                    full_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "category_slug": category_slug,
                        "playwright": False,
                    },
                )

            if not links and not products:
                self.logger.warning(f"No products found on {response.url}")
                return

        self.logger.info(
            f"Category page: {product_count} new products from {response.url}"
        )

        # Pagination — stop if no products or stopFurtherCall
        if product_count == 0 or stop_further:
            return

        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            next_url = f"{base_url}?page_no={next_page}"
            self._pages_followed[base_url] = next_page

            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "playwright": False,
                },
                dont_filter=True,
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page.

        Strategies (tried in order):
          1. __PRELOADED_STATE__ → productPage.product
          2. JSON-LD Product schema
          3. Listing data passed via meta (last resort)
        """
        self._product_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        if response.status == 404:
            self.logger.debug(f"404 on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        # Extract product ID from URL
        id_match = PRODUCT_ID_RE.search(response.url)
        external_id = id_match.group(1) if id_match else None

        # Strategy 1: __PRELOADED_STATE__ → productPage.product
        state = self._extract_preloaded_state(response)
        if state:
            product = self._find_product_in_state(state)
            if product:
                item = self._parse_from_state(
                    product, response.url, category_slug, external_id,
                )
                if item:
                    self._products_extracted += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug, external_id)
        if item:
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: Build from listing data passed via meta
        if listing_data:
            item = self._parse_from_listing_data(
                listing_data, response, category_slug, external_id,
            )
            if item:
                self._products_extracted += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(
            f"Could not extract product data from {response.url}"
        )
        self.items_failed += 1

    # ------------------------------------------------------------------
    # State navigation helper
    # ------------------------------------------------------------------

    def _find_product_in_state(self, state: dict) -> dict | None:
        """Find the product object within the Redux state tree."""
        # Direct path: productPage.product
        pp = state.get("productPage", {})
        product = pp.get("product")
        if isinstance(product, dict) and product.get("name"):
            return product

        # Alternative paths
        for key in ("productPage", "product", "pdp"):
            section = state.get(key, {})
            if not isinstance(section, dict):
                continue
            if section.get("name"):
                return section
            for inner_key in ("product", "productDetails", "data"):
                inner = section.get(inner_key)
                if isinstance(inner, dict) and inner.get("name"):
                    return inner
        return None

    # ------------------------------------------------------------------
    # Extraction: __PRELOADED_STATE__ (primary)
    # ------------------------------------------------------------------

    def _parse_from_state(
        self,
        product: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from __PRELOADED_STATE__ product object."""
        name = product.get("name") or product.get("title")
        if not name:
            return None

        pid = external_id or str(
            product.get("id") or product.get("productId") or ""
        )
        if not pid:
            return None

        # Prices (Nykaa uses offerPrice for selling, mrp for MRP)
        selling_price = self._parse_price(
            product.get("offerPrice") or product.get("price")
        )
        mrp = self._parse_price(product.get("mrp"))

        # Brand
        brand = product.get("brandName") or product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        # Images
        images = self._extract_images_from_state(product)

        # Rating
        rating = None
        review_count = None
        rating_val = product.get("rating") or product.get("averageRating")
        if rating_val and str(rating_val) not in ("0", "0.0", ""):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = product.get("reviewCount") or product.get("totalReviews")
        if count_val and str(count_val) not in ("0", ""):
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = product.get("inStock", True)

        # Description (strip HTML tags)
        description = product.get("description") or product.get(
            "productDescription"
        )
        if description:
            description = re.sub(r"<[^>]+>", " ", str(description))
            description = re.sub(r"\s+", " ", description).strip()[:5000]

        # Seller
        seller_name = product.get("sellerName") or "Nykaa"

        # Manufacturer info
        manufacturer = product.get("manufacturerName")
        country_of_origin = product.get("originOfCountryName")
        manufacture_info = product.get("manufacture")
        if isinstance(manufacture_info, list) and manufacture_info:
            info = manufacture_info[0]
            if not manufacturer:
                manufacturer = info.get("manufacturerName")
            if not country_of_origin:
                country_of_origin = info.get("originOfCountryName")

        # Category from product data
        if not category_slug:
            cat_name = (
                product.get("categoryName")
                or product.get("category")
                or ""
            ).lower()
            for kw, slug in KEYWORD_CATEGORY_MAP.items():
                if kw in cat_name:
                    category_slug = slug
                    break

        # Variants
        variants = product.get("variants", [])
        variant_options = []
        if isinstance(variants, list):
            for v in variants[:20]:
                if isinstance(v, dict):
                    variant_options.append({
                        "name": v.get("name", ""),
                        "id": str(v.get("id", "")),
                    })

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs={},
            seller_name=seller_name,
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="Nykaa",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=None,
            delivery_info=None,
            return_policy=product.get("returnMessage"),
            breadcrumbs=[],
            variant_options=variant_options,
            country_of_origin=str(country_of_origin) if country_of_origin else None,
            manufacturer=str(manufacturer) if manufacturer else None,
            model_number=product.get("sku"),
            weight=product.get("packSize"),
            dimensions=None,
        )

    def _extract_images_from_state(self, product: dict) -> list[str]:
        """Extract product images from state object."""
        images: list[str] = []
        seen: set[str] = set()

        def _add(url: str) -> None:
            if not url or url.startswith("data:"):
                return
            # Normalize
            clean = url.split("?")[0] if "?" in url else url
            if clean.startswith("//"):
                clean = "https:" + clean
            if clean not in seen:
                seen.add(clean)
                images.append(clean)

        # Single image field
        for key in ("imageUrl", "thumbnailUrl", "image"):
            img = product.get(key)
            if isinstance(img, str) and img:
                _add(img)

        # Image list fields
        for key in ("imageUrls", "images", "mediaGallery", "parentMedia"):
            img_list = product.get(key)
            if isinstance(img_list, list):
                for img in img_list:
                    if isinstance(img, str):
                        _add(img)
                    elif isinstance(img, dict):
                        _add(img.get("url") or img.get("src") or "")

        return images

    # ------------------------------------------------------------------
    # Extraction: JSON-LD (fallback)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self,
        response,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from JSON-LD structured data."""
        # First try __PRELOADED_STATE__.jsonLdData
        state = self._extract_preloaded_state(response)
        ld_blocks = []
        if state:
            ld_blocks = state.get("jsonLdData", [])

        # Also try from HTML script tags
        ld_scripts = response.css(
            'script[type="application/ld+json"]::text'
        ).getall()
        for script_text in ld_scripts:
            try:
                ld_data = json.loads(script_text)
                if isinstance(ld_data, list):
                    ld_blocks.extend(ld_data)
                else:
                    ld_blocks.append(ld_data)
            except (json.JSONDecodeError, ValueError):
                continue

        for ld_data in ld_blocks:
            if not isinstance(ld_data, dict):
                continue
            if ld_data.get("@type") != "Product":
                continue

            name = ld_data.get("name")
            if not name:
                continue

            sku = ld_data.get("sku") or ld_data.get("mpn") or external_id
            if not sku:
                continue

            offers = ld_data.get("offers", {})
            if isinstance(offers, list) and offers:
                offers = offers[0]
            price = self._parse_price(offers.get("price"))

            brand_data = ld_data.get("brand", {})
            if isinstance(brand_data, dict):
                brand = brand_data.get("name")
            elif brand_data:
                brand = str(brand_data)
            else:
                brand = None

            images = ld_data.get("image", [])
            if isinstance(images, str):
                images = [images]

            rating = None
            review_count = None
            agg_rating = ld_data.get("aggregateRating", {})
            if isinstance(agg_rating, dict):
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
            if "OutOfStock" in str(availability):
                in_stock = False

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url,
                title=name,
                brand=brand,
                price=price,
                mrp=None,
                images=images if isinstance(images, list) else [],
                rating=rating,
                review_count=review_count,
                specs={},
                seller_name="Nykaa",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="Nykaa",
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
    # Extraction: From listing data passed via meta (last resort)
    # ------------------------------------------------------------------

    def _parse_from_listing_data(
        self,
        listing: dict,
        response,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build a ProductItem from listing data when detail page fails."""
        name = listing.get("name") or listing.get("title")
        if not name:
            return None

        pid = external_id or str(
            listing.get("id") or listing.get("productId") or ""
        )
        if not pid:
            return None

        selling_price = self._parse_price(
            listing.get("offerPrice") or listing.get("price")
        )
        mrp = self._parse_price(listing.get("mrp"))

        brand = listing.get("brandName") or listing.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = []
        img = listing.get("imageUrl") or listing.get("thumbnailUrl")
        if isinstance(img, str) and img:
            images = [img]

        rating = None
        if listing.get("rating"):
            try:
                rating = Decimal(str(listing["rating"]))
                if rating <= 0:
                    rating = None
            except (InvalidOperation, ValueError):
                pass

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=response.url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=None,
            specs={},
            seller_name="Nykaa",
            seller_rating=None,
            in_stock=listing.get("inStock", True),
            fulfilled_by="Nykaa",
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
