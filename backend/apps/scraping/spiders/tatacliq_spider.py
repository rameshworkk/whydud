"""Tata CLiQ spider — Playwright-based SPA scraper with XHR interception.

Architecture:
  TataCLiQ is a PURE SPA — every URL returns an empty <div id="root">.
  ALL product data is loaded via XHR/fetch after React hydration.
  __NEXT_DATA__ does NOT exist on this site.

  Strategy:
    1. Load pages via Playwright (stealth + DataImpulse proxy)
    2. Intercept XHR/fetch responses for structured JSON data
    3. Fallback: extract from rendered DOM after React render
    4. Fallback: JSON-LD (if present on product pages)

  Discovery: SEARCH-BASED — category URLs no longer work (SPA routes to 404).
    Uses /search/?searchCategory=all&text={keyword} to find products.

  Anti-bot: Cloudflare Bot Management (__cf_bm cookie)
  Proxy: DataImpulse rotating proxy (required for sustained scraping)

  All prices in RUPEES — converted to paisa (* 100) before yielding.

URL patterns:
  Search:   /search/?searchCategory=all&text={query}&page={n}
  Product:  /{product-slug}/p-{mp+code}
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

PRODUCT_CODE_RE = re.compile(r"/p-(\w+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "tata_cliq"

# DataImpulse rotating proxy — each connection gets a different exit IP.
# Set SCRAPING_PROXY_LIST env var or leave empty to run without proxy.
import os as _os
_PROXY_URL = _os.environ.get("SCRAPING_PROXY_LIST", "").strip().split(",")[0].strip()
DATAIMPULSE_PROXY: dict | None = None
if _PROXY_URL:
    from urllib.parse import urlparse as _urlparse
    _parsed = _urlparse(_PROXY_URL)
    DATAIMPULSE_PROXY = {
        "server": f"{_parsed.scheme}://{_parsed.hostname}:{_parsed.port}",
    }
    if _parsed.username:
        DATAIMPULSE_PROXY["username"] = _parsed.username
    if _parsed.password:
        DATAIMPULSE_PROXY["password"] = _parsed.password

# Playwright context kwargs shared by all requests.
_PW_CONTEXT_BASE: dict = {
    "locale": "en-IN",
    "timezone_id": "Asia/Kolkata",
    "java_script_enabled": True,
    "ignore_https_errors": True,
    "bypass_csp": True,
    "extra_http_headers": {
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
    },
}
if DATAIMPULSE_PROXY:
    _PW_CONTEXT_BASE["proxy"] = DATAIMPULSE_PROXY

# Two context slots — forces IP rotation on DataImpulse.
_CONTEXT_NAMES = ["tcliq_0", "tcliq_1"]

# Viewports randomized per context to reduce fingerprinting.
_VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1536, "height": 864},
    {"width": 1440, "height": 900},
]

# ---------------------------------------------------------------------------
# XHR / fetch interception — injected BEFORE page scripts load
# ---------------------------------------------------------------------------

_XHR_CAPTURE_JS = """
window.__whydud_xhr = [];
const _wf = window.fetch;
window.fetch = async function() {
    const r = await _wf.apply(this, arguments);
    try {
        const a0 = arguments[0];
        const u = typeof a0 === 'string' ? a0 : (a0 && a0.url ? a0.url : (r.url || ''));
        if (r.ok) {
            const c = r.headers.get('content-type') || '';
            if (c.includes('json')) {
                const d = await r.clone().json();
                window.__whydud_xhr.push({u: u, d: d});
            }
        }
    } catch(e) {}
    return r;
};
const _xo = XMLHttpRequest.prototype.open;
const _xs = XMLHttpRequest.prototype.send;
XMLHttpRequest.prototype.open = function(m, u) {
    this._wu = u;
    return _xo.apply(this, arguments);
};
XMLHttpRequest.prototype.send = function() {
    this.addEventListener('load', function() {
        try {
            const c = this.getResponseHeader('content-type') || '';
            if (c.includes('json') && this._wu) {
                window.__whydud_xhr.push({u: this._wu, d: JSON.parse(this.responseText)});
            }
        } catch(e) {}
    });
    return _xs.apply(this, arguments);
};
"""

# Evaluated AFTER page load — injects captured XHR data into DOM.
_XHR_INJECT_JS = """() => {
    try {
        const e = document.createElement('script');
        e.id = '__whydud_data';
        e.type = 'application/json';
        e.textContent = JSON.stringify(window.__whydud_xhr || []);
        document.head.appendChild(e);
    } catch(x) {}
    return (window.__whydud_xhr || []).length;
}"""

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "electronics": "electronics",
    "mobile-phones": "smartphones",
    "smartphones": "smartphones",
    "laptop": "laptops",
    "tv": "televisions",
    "head-phones": "audio",
    "earphones": "audio",
    "speakers": "audio",
    "audio-video": "audio",
    "camera": "cameras",
    "tablets": "tablets",
    "wearable-devices": "smartwatches",
    "smart-watch": "smartwatches",
    "mens-clothing": "mens-fashion",
    "womens-clothing": "womens-fashion",
    "large-appliances": "appliances",
    "refrigerators": "refrigerators",
    "washing-machine": "washing-machines",
    "air-conditioner": "air-conditioners",
    "small-appliances": "appliances",
}

# ---------------------------------------------------------------------------
# Seed queries — search-based discovery (category URLs route to SPA 404)
# Format: (search_term, whydud_category_slug, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_SEARCH_QUERIES: list[tuple[str, str, int]] = [
    # NOTE: TataCLiQ's SPA redirects many generic terms (e.g. "laptops",
    # "television", "mobile phones") to a curated promo/CLP page. These are
    # detected as blocks and skipped. Brand-specific queries work more reliably.
    #
    # Tested working (2026-03): "smartphones", "headphones earphones"
    # Order: put known-working queries first for quick mode.

    # Known-working queries
    ("smartphones", "smartphones", _TOP),
    ("headphones earphones", "audio", _STD),
    ("bluetooth speakers", "audio", _STD),
    ("smartwatch", "smartwatches", _STD),

    # Brand-specific queries — higher success rate
    ("samsung mobile", "smartphones", _STD),
    ("iphone", "smartphones", _STD),
    ("oneplus phone", "smartphones", _STD),
    ("sony headphones", "audio", _STD),
    ("jbl speaker", "audio", _STD),
    ("samsung tv", "televisions", _STD),
    ("lg tv", "televisions", _STD),
    ("laptop dell", "laptops", _STD),
    ("laptop hp", "laptops", _STD),
    ("macbook", "laptops", _STD),
    ("dslr camera", "cameras", _STD),
    ("ipad tablet", "tablets", _STD),

    # Appliances
    ("refrigerator samsung", "refrigerators", _STD),
    ("washing machine lg", "washing-machines", _STD),
    ("air conditioner", "air-conditioners", _STD),

    # Fashion
    ("mens shirt", "mens-fashion", _STD),
    ("womens dress", "womens-fashion", _STD),
    ("mens jeans", "mens-fashion", _STD),
]

_SEARCH_URL = "https://www.tatacliq.com/search/?searchCategory=all&text={query}"

MAX_LISTING_PAGES = 5
PAGE_SIZE = 40
QUICK_MODE_CATEGORIES = 5


class TataCliqSpider(BaseWhydudSpider):
    """Scrapes TataCLiQ.com — pure SPA with Cloudflare Bot Management.

    Uses Playwright + stealth + DataImpulse proxy for ALL pages.
    Primary extraction via XHR/fetch response interception.
    Fallback via rendered DOM parsing and JSON-LD.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "tata_cliq"
    allowed_domains = ["tatacliq.com", "www.tatacliq.com"]

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
        "PLAYWRIGHT_MAX_CONTEXTS": 3,  # 2 proxy + 1 default
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
        self._ctx_idx: int = 0

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._products_extracted: int = 0
        self._xhr_extractions: int = 0
        self._dom_extractions: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"TataCLiQ spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"xhr_extractions={self._xhr_extractions}, "
            f"dom_extractions={self._dom_extractions}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Playwright helpers
    # ------------------------------------------------------------------

    async def _page_init(self, page, request):
        """Apply stealth and inject XHR capture script before navigation."""
        try:
            await self.STEALTH.apply_stealth_async(page)
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(45000)
        except Exception as e:
            self.logger.warning(f"Stealth setup issue: {e}")

        await page.add_init_script(_XHR_CAPTURE_JS)

    def _next_context(self) -> str:
        """Cycle between 2 proxy context slots for IP rotation."""
        name = _CONTEXT_NAMES[self._ctx_idx % len(_CONTEXT_NAMES)]
        self._ctx_idx += 1
        return name

    def _pw_meta(
        self, category_slug: str | None = None, wait_ms: tuple[int, int] = (8000, 15000),
        extra: dict | None = None,
    ) -> dict:
        """Build Playwright request meta with proxy, stealth, and XHR capture."""
        ctx_name = self._next_context()
        vp = random.choice(_VIEWPORTS)
        meta = {
            "category_slug": category_slug,
            "playwright": True,
            # Spider manages its own proxy context — skip middleware override.
            "_skip_proxy_middleware": True,
            "playwright_context": ctx_name,
            "playwright_context_kwargs": {**_PW_CONTEXT_BASE, "viewport": vp},
            "playwright_page_init_callback": self._page_init,
            "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
            "playwright_page_methods": [
                # Wait for React SPA to hydrate and fetch search results
                PageMethod("wait_for_timeout", random.randint(*wait_ms)),
                # Inject captured XHR data into DOM for extraction
                PageMethod("evaluate", _XHR_INJECT_JS),
            ],
        }
        if extra:
            meta.update(extra)
        return meta

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """First visit homepage (warmup for Cloudflare cookies), then search pages."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}")
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        # Step 1: Warmup — visit homepage to establish Cloudflare cookies/session.
        # Uses tcliq_0 context so subsequent requests on the same context share cookies.
        self.logger.info("Warmup: visiting TataCLiQ homepage to establish session")
        yield scrapy.Request(
            "https://www.tatacliq.com/",
            callback=self._after_warmup,
            errback=self._warmup_failed,
            headers=self._make_headers(),
            meta=self._pw_meta(wait_ms=(8000, 12000)),
            dont_filter=True,
        )

    def _after_warmup(self, response):
        """Homepage loaded — now queue search pages using the established session."""
        if self._is_blocked(response):
            self.logger.warning(
                f"Homepage warmup blocked (status={response.status}, url={response.url}). "
                "Proceeding anyway — search pages may fail."
            )
        else:
            self.logger.info(
                f"Homepage warmup OK (status={response.status}, "
                f"url={response.url}, body={len(response.body)} bytes)"
            )

        yield from self._queue_search_requests()

    def _warmup_failed(self, failure):
        """Homepage warmup failed — still try search pages."""
        self.logger.warning(f"Homepage warmup failed: {failure.getErrorMessage()}")
        yield from self._queue_search_requests()

    def _queue_search_requests(self):
        """Yield search page requests."""
        queries = self._load_queries()
        random.shuffle(queries)

        for url, category_slug, max_pg in queries:
            self._max_pages_map[url] = max_pg
            self.logger.info(f"Queuing search ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta=self._pw_meta(category_slug=category_slug),
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(queries)} search queries (Playwright + proxy)")

    def _load_queries(self) -> list[tuple[str, str, int]]:
        """Resolve (url, category_slug, max_pages) list to crawl."""
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        # Override: explicit URLs (still supported for ad-hoc runs)
        if self._category_urls:
            return [
                (u, self._resolve_category_from_url(u), fallback)
                for u in self._category_urls
            ]

        # Build search URLs from seed queries
        seeds = SEED_SEARCH_QUERIES
        if self._max_pages_override is not None:
            max_pg = self._max_pages_override
            if max_pg <= 3:
                self.logger.info(
                    f"Quick mode: {QUICK_MODE_CATEGORIES} queries, "
                    f"max_pages={max_pg}"
                )
                seeds = seeds[:QUICK_MODE_CATEGORIES]
        else:
            max_pg = None  # use per-query default

        result = []
        for query, cat_slug, default_max in seeds:
            url = _SEARCH_URL.format(query=query.replace(" ", "+"))
            result.append((url, cat_slug, max_pg if max_pg is not None else default_max))
        return result

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products directly from listing page (XHR or DOM).

        Strategy: yield ProductItems directly from listing data — avoids
        visiting individual product pages (which fail with proxy auth errors).
        """
        self._listing_pages_scraped += 1

        self.logger.info(
            f"Listing page: status={response.status}, url={response.url}, "
            f"body={len(response.body)} bytes"
        )

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")
        items_yielded = 0

        # Strategy 1: XHR intercepted data (primary — Hybris searchab API)
        xhr_data = self._extract_xhr_data(response)
        if xhr_data:
            xhr_urls = [entry.get("u", "?")[:100] for entry in xhr_data[:10]]
            self.logger.info(f"XHR captured {len(xhr_data)} responses, URLs: {xhr_urls}")
        else:
            self.logger.warning("No XHR data captured — init script may not have injected")

        products = self._find_products_in_xhr(xhr_data)
        if products:
            self.logger.info(
                f"Found {len(products)} products (XHR) on {response.url}"
            )
            for prod in products:
                item = self._build_item_from_listing(prod, category_slug)
                if item:
                    self._xhr_extractions += 1
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    items_yielded += 1
                    yield item

        # Strategy 2: Extract from rendered DOM (product cards)
        if items_yielded == 0:
            dom_items = self._extract_from_dom(response, category_slug)
            for item in dom_items:
                self._dom_extractions += 1
                self._product_pages_scraped += 1
                self.items_scraped += 1
                items_yielded += 1
                yield item

        if items_yielded > 0:
            self.logger.info(f"Yielded {items_yielded} items from listing {response.url}")
        else:
            self.logger.warning(
                f"No products extracted from {response.url} "
                f"(XHR: {len(xhr_data)} responses)"
            )
            return

        # Pagination — preserve full query string
        yield from self._follow_pagination(response, category_slug)

    def _follow_pagination(self, response, category_slug: str | None):
        """Build next page URL preserving search query params."""
        from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

        parsed = urlparse(response.url)
        params = parse_qs(parsed.query)

        # Track pages by the base search query (not full URL with page params)
        base_key = parsed.path
        pages_so_far = self._pages_followed.get(base_key, 0)

        # Determine max pages for this search
        original_url = response.meta.get("_original_search_url", response.url)
        max_for_search = self._max_pages_map.get(original_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_search - 1:
            next_page = pages_so_far + 1
            # Preserve search params, update page
            params["page"] = [str(next_page)]
            params["size"] = [str(PAGE_SIZE)]
            new_query = urlencode(
                {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
            )
            next_url = urlunparse(parsed._replace(query=new_query))
            self._pages_followed[base_key] = next_page

            self.logger.info(f"Following pagination → {next_url}")
            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta=self._pw_meta(
                    category_slug=category_slug,
                    extra={"_original_search_url": original_url},
                ),
            )

    def _extract_from_dom(self, response, category_slug: str | None) -> list:
        """Extract product data from rendered DOM product cards."""
        items = []
        # TataCLiQ product cards typically have links to /p-{code}
        product_links = response.css("a[href*='/p-']")
        seen_urls = set()

        for link in product_links:
            href = link.attrib.get("href", "")
            full_url = response.urljoin(href)
            if full_url in seen_urls or "/p-" not in full_url:
                continue
            seen_urls.add(full_url)

            code_match = PRODUCT_CODE_RE.search(full_url)
            external_id = code_match.group(1) if code_match else None
            if not external_id:
                continue

            # Try to get title from the link or nearby elements
            title = link.css("::text").get() or ""
            title = title.strip()
            if not title or len(title) < 5:
                # Try parent container
                parent = link.xpath("ancestor::div[contains(@class,'product')]")
                if parent:
                    title = " ".join(parent.css("::text").getall()).strip()[:200]

            if not title or len(title) < 5:
                continue

            # Try to extract price from nearby elements
            parent_card = link.xpath("ancestor::div[contains(@class,'ProductCard') or contains(@class,'product-card') or contains(@class,'ProductModule')]")
            price = None
            if parent_card:
                price_texts = parent_card.re(r'₹\s*([\d,]+)')
                if price_texts:
                    price = self._parse_price(price_texts[0])

            # Image
            img = link.css("img::attr(src)").get()
            images = [img] if img else []

            item = ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=external_id,
                url=full_url,
                title=title,
                brand=None,
                price=price,
                mrp=None,
                images=images,
                rating=None,
                review_count=None,
                specs={},
                seller_name="TataCLiQ",
                seller_rating=None,
                in_stock=True,
                fulfilled_by="TataCLiQ",
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
            items.append(item)

        self.logger.info(f"DOM extraction: {len(items)} products from {len(seen_urls)} links")
        return items

    def _build_item_from_listing(self, data: dict, category_slug: str | None) -> ProductItem | None:
        """Build a ProductItem from listing XHR data (no product page visit)."""
        return self._build_item(
            data,
            url=self._product_url_from_data(data),
            category_slug=category_slug,
            external_id=str(
                data.get("productId") or data.get("productCode") or data.get("id") or ""
            ) or None,
        )

    def _product_url_from_data(self, data: dict) -> str:
        """Build a product URL from listing data."""
        slug = data.get("url") or data.get("slug") or ""
        if slug and slug.startswith("/"):
            return f"https://www.tatacliq.com{slug}"
        elif slug:
            return f"https://www.tatacliq.com/{slug}"
        pid = data.get("productId") or data.get("productCode") or data.get("id")
        if pid:
            return f"https://www.tatacliq.com/p-{pid}"
        return ""

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page via XHR or DOM."""
        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        code_match = PRODUCT_CODE_RE.search(response.url)
        external_id = code_match.group(1) if code_match else None

        # Strategy 1: XHR intercepted data
        xhr_data = self._extract_xhr_data(response)
        product = self._find_product_detail_in_xhr(xhr_data)
        if product:
            item = self._build_item(product, response.url, category_slug, external_id)
            if item:
                self._xhr_extractions += 1
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug, external_id)
        if item:
            self._dom_extractions += 1
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: Listing data fallback
        if listing_data:
            item = self._build_item(listing_data, response.url, category_slug, external_id)
            if item:
                self._dom_extractions += 1
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        # Strategy 4: Redux store via JS evaluation
        # (window.__STORE__ or similar — last resort)
        # The PageMethod already ran, so we check for any store data
        # that may have been captured.

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # XHR data extraction
    # ------------------------------------------------------------------

    def _extract_xhr_data(self, response) -> list[dict]:
        """Extract captured XHR/fetch JSON responses from injected DOM element."""
        script = response.css('script#__whydud_data::text').get()
        if not script:
            return []
        try:
            return json.loads(script)
        except (json.JSONDecodeError, ValueError):
            return []

    def _find_products_in_xhr(self, xhr_data: list[dict]) -> list[dict]:
        """Search XHR responses for product listing arrays.

        Prioritizes the Hybris searchab API (marketplacewebservices/v2/mpl/products)
        since it contains the richest product data.
        """
        # First pass: look specifically for the Hybris search API response
        for entry in xhr_data:
            url = entry.get("u", "")
            if "searchab" in url or "products/search" in url or "marketplacewebservices" in url:
                data = entry.get("d", {})
                if isinstance(data, dict):
                    products = self._extract_product_list(data)
                    if products:
                        self.logger.info(f"Found {len(products)} products from Hybris API: {url[:80]}")
                        return products

        # Second pass: generic patterns
        for entry in xhr_data:
            data = entry.get("d", {})
            if not isinstance(data, dict):
                continue

            products = self._extract_product_list(data)
            if products:
                return products

        return []

    def _extract_product_list(self, data: dict) -> list[dict]:
        """Try to extract a product list from an XHR response dict."""
        # Direct product array keys
        for key in ("products", "results", "items", "productList",
                     "searchProducts", "data", "searchresult"):
            val = data.get(key)
            if isinstance(val, list) and val and isinstance(val[0], dict):
                if self._looks_like_products(val):
                    return val

        # Nested search — e.g. data.searchResult.products
        for outer_key in ("searchResult", "categoryData", "plpData",
                          "response", "searchresult", "plpResponse"):
            section = data.get(outer_key)
            if not isinstance(section, dict):
                continue
            for key in ("products", "results", "items", "productList"):
                val = section.get(key)
                if isinstance(val, list) and val and isinstance(val[0], dict):
                    if self._looks_like_products(val):
                        return val

        return []

    def _looks_like_products(self, items: list[dict]) -> bool:
        """Check if a list of dicts looks like product data."""
        first = items[0]
        return any(
            k in first
            for k in (
                "productId", "productCode", "name", "productname",
                "id", "url", "price", "winningSellerPrice",
                "imageURL", "brandname",
            )
        )

        return []

    def _find_product_detail_in_xhr(self, xhr_data: list[dict]) -> dict | None:
        """Search XHR responses for a single product detail object."""
        for entry in xhr_data:
            data = entry.get("d", {})
            if not isinstance(data, dict):
                continue

            # Direct product object
            for key in ("productData", "product", "productDetails"):
                val = data.get(key)
                if isinstance(val, dict) and (val.get("productname") or val.get("name")):
                    return val

            # Top-level product data
            if data.get("productname") or (data.get("name") and data.get("productId")):
                return data

        return None

    # ------------------------------------------------------------------
    # Item builders
    # ------------------------------------------------------------------

    def _build_item(
        self, data: dict, url: str, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Build a ProductItem from a product data dict (XHR or listing)."""
        name = data.get("productname") or data.get("name")
        if not name:
            return None

        pid = external_id or str(
            data.get("productId") or data.get("productCode") or data.get("id") or ""
        )
        if not pid:
            return None

        selling_price = self._parse_price(
            data.get("price") or data.get("winningSellerPrice")
        )
        mrp = self._parse_price(data.get("mrp") or data.get("wasPriceData"))

        brand = data.get("brandname") or data.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = self._extract_images(data)

        rating = None
        review_count = None
        rating_val = data.get("averageRating") or data.get("rating")
        if rating_val and str(rating_val) not in ("0", "0.0"):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = data.get("totalRatings") or data.get("reviewCount") or data.get("ratingCount")
        if count_val and str(count_val) != "0":
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        in_stock = data.get("inStock", True)
        seller_name = data.get("sellerName") or data.get("winningSellerName") or "TataCLiQ"

        if not category_slug:
            hierarchy = data.get("categoryHierarchy") or []
            for cat in hierarchy:
                cat_lower = cat.lower() if isinstance(cat, str) else ""
                for kw, slug in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_lower:
                        category_slug = slug
                        break
                if category_slug:
                    break

        description = data.get("description") or data.get("productDescription")

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=name,
            brand=brand if brand else None,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs={},
            seller_name=seller_name,
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="TataCLiQ",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
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

    def _extract_images(self, data: dict) -> list[str]:
        """Extract image URLs from product data."""
        images = []
        for key in ("imageURL", "image", "productImage"):
            img = data.get(key)
            if img:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, list):
                    images.extend(i for i in img if isinstance(i, str))
        gallery = data.get("galleryImages") or data.get("images") or []
        for img in gallery:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                images.append(img.get("url") or img.get("imageURL", ""))
        return [i for i in images if i]

    # ------------------------------------------------------------------
    # JSON-LD fallback
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self, response, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from JSON-LD structured data."""
        for script_text in response.css('script[type="application/ld+json"]::text').getall():
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
            sku = ld_data.get("sku") or external_id
            if not name or not sku:
                continue

            offers = ld_data.get("offers") or {}
            if isinstance(offers, list) and offers:
                offers = offers[0]
            price = self._parse_price(offers.get("price"))

            brand_data = ld_data.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data) if brand_data else None

            images = ld_data.get("image") or []
            if isinstance(images, str):
                images = [images]

            in_stock = "OutOfStock" not in (offers.get("availability") or "")

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
                seller_name=(
                    offers.get("seller", {}).get("name", "TataCLiQ")
                    if isinstance(offers.get("seller"), dict)
                    else "TataCLiQ"
                ),
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="TataCLiQ",
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
    # Utility helpers
    # ------------------------------------------------------------------

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value to Decimal in paisa (rupees × 100)."""
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
        """Detect Cloudflare challenge, block page, or SPA redirect to /404."""
        if response.status in (403, 429, 503):
            self.logger.debug(f"Blocked: HTTP {response.status}")
            return True
        # TataCLiQ SPA redirects to /404 when bot-detected or URL is invalid.
        final_url = response.url
        if "/404" in final_url or final_url.rstrip("/").endswith("/404"):
            self.logger.debug(f"Blocked: URL contains /404: {final_url}")
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        self.logger.debug(f"Page title: {title!r}")
        if "just a moment" in title or "attention required" in title:
            return True
        if "access denied" in title or "blocked" in title:
            return True
        if "page not found" in title or "404" in title:
            return True
        # Check for Cloudflare challenge markers in body — only flag if it's
        # a challenge page (small body), not if "captcha" appears incidentally
        # in a large SPA bundle.
        body_prefix = response.text[:3000].lower() if response.text else ""
        if len(response.body) < 50000 and (
            "captcha" in body_prefix or "robot check" in body_prefix
        ):
            self.logger.debug(f"Blocked: CAPTCHA marker in small page ({len(response.body)} bytes)")
            return True
        # Redirected to TataCLiQ's generic CLP instead of search results —
        # indicates the search was intercepted/blocked.
        if "gadget-clp" in final_url or "icid2=" in final_url:
            self.logger.debug(f"Blocked: redirected to promo CLP: {final_url[:100]}")
            return True
        return False

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path."""
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None
