"""JioMart spider — sitemap-based discovery + HTTP product detail parsing.

Architecture:
  Phase 1 (Discovery): Parse sitemap.xml → sub-sitemaps → product URLs.
    JioMart's listing/search pages are 100% client-rendered (Algolia) and
    CANNOT be scraped without Playwright. robots.txt explicitly disallows
    /search and /*? — we respect this and use sitemaps instead.
  Phase 2 (Detail): HTTP GET each product URL → parse SSR HTML for
    product name, prices, brand, specs, seller, images.

  NO Playwright — HTTP only.

  Prices on JioMart are in RUPEES (not paisa). Spider converts to paisa
  (* 100) before yielding.

  Akamai WAF requires Sec-Fetch-* headers AND a browser-like TLS
  fingerprint — HEAD requests return 403. Only GET works. Uses curl_cffi
  with Chrome TLS impersonation (same approach as Nykaa spider) because
  Python's standard ssl/urllib3 TLS fingerprint is blocked by Akamai.

  Product URL pattern: https://www.jiomart.com/p/{vertical}/{slug}/{sku_id}

Sitemaps (discovered 2026-03-03):
  Main: https://www.jiomart.com/sitemap.xml
  Sub-sitemaps: electronics.xml, fashion.xml, gm-sitemap.xml,
    fmcg-sitemap.xml, cdit-sitemap.xml, website.xml
  Dated 2023-12 to 2024-04 — may have stale URLs, handle 404s gracefully.

Prices are pincode-dependent — defaults to Mumbai (400020). Fine for v1.
"""
import json
import logging
import re
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree

import scrapy
from scrapy import signals
from scrapy.http import HtmlResponse, TextResponse

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MARKETPLACE_SLUG = "jiomart"

SITEMAP_INDEX_URL = "https://www.jiomart.com/sitemap.xml"

# Chrome/131 User-Agent — used for all JioMart requests
JIOMART_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Required headers for Akamai bypass — applied by CurlCffiMiddleware
JIOMART_HEADERS = {
    "User-Agent": JIOMART_USER_AGENT,
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
    "sec-ch-ua": '"Chromium";v="131", "Not_A Brand";v="24", "Google Chrome";v="131"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


# ===================================================================
# CurlCffi downloader middleware — Chrome TLS impersonation for Akamai
# ===================================================================

class JioMartCurlCffiMiddleware:
    """Scrapy downloader middleware that uses curl_cffi for JioMart requests.

    Akamai Bot Manager fingerprints TLS handshakes (JA3/JA4).
    Python's ssl module and Twisted have a distinct fingerprint that's
    blocked (403). curl_cffi wraps libcurl and can impersonate a real
    Chrome browser's TLS handshake.
    """

    def __init__(self) -> None:
        from curl_cffi import requests as curl_requests
        self._session = curl_requests.Session(impersonate="chrome131")
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
        # Only handle non-Playwright requests to jiomart.com
        if request.meta.get("playwright"):
            return None
        if "jiomart.com" not in request.url:
            return None

        self._request_count += 1

        # Use Accept: text/xml for sitemap requests
        headers = dict(JIOMART_HEADERS)
        if "sitemap" in request.url.lower() or request.url.endswith(".xml"):
            headers["Accept"] = "text/xml,application/xml,text/html,*/*;q=0.8"

        try:
            resp = self._session.get(
                request.url,
                headers=headers,
                timeout=60,
                allow_redirects=True,
            )

            # curl_cffi already decompresses gzip/brotli — strip the
            # Content-Encoding header so Scrapy doesn't try again.
            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() != "content-encoding"
            }

            # Use TextResponse for XML sitemaps, HtmlResponse for product pages
            if "sitemap" in request.url.lower() or request.url.endswith(".xml"):
                return TextResponse(
                    url=str(resp.url),
                    status=resp.status_code,
                    headers=resp_headers,
                    body=resp.content,
                    request=request,
                    encoding="utf-8",
                )
            return HtmlResponse(
                url=str(resp.url),
                status=resp.status_code,
                headers=resp_headers,
                body=resp.content,
                request=request,
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning(f"curl_cffi request failed for {request.url}: {exc}")
            return None

PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

# XML namespace used in sitemap files
SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Product URL pattern — /p/{vertical}/{slug}/{sku_id}
PRODUCT_URL_RE = re.compile(r"/p/[^/]+/[^/]+/\d+")

# SKU ID from URL — last numeric segment
SKU_ID_RE = re.compile(r"/(\d+)$")

# Default number of product URLs to process per sitemap
# (overridden by --max-pages: urls_per_sitemap = max_pages * 50)
DEFAULT_URLS_PER_SITEMAP = 250

# ---------------------------------------------------------------------------
# Sub-sitemaps to follow for v1 (skip groceries/FMCG)
# Maps sub-sitemap filename pattern → category slug hint
# ---------------------------------------------------------------------------

ALLOWED_SITEMAPS: dict[str, str] = {
    "electronics": "electronics",
    "cdit": "electronics",
    "home": "home-improvement",
}

# ---------------------------------------------------------------------------
# Vertical → Whydud category slug mapping (from URL path segment)
# ---------------------------------------------------------------------------

VERTICAL_CATEGORY_MAP: dict[str, str] = {
    "electronics": "electronics",
    "fashion": "fashion",
    "homeandkitchen": "home-kitchen",
    "homeimprovement": "home-improvement",
    "beauty": "beauty",
    "wellness": "wellness",
    "jewellery": "jewellery",
}


class JioMartSpider(BaseWhydudSpider):
    """Scrapes JioMart.com via sitemap discovery + SSR HTML product pages.

    Two-phase architecture — NO Playwright required:
      Phase 1: Parse sitemap XML index → sub-sitemaps → product URLs
      Phase 2: HTTP GET product pages → parse SSR HTML

    Prices on JioMart are in INR (rupees), NOT paisa. Spider converts.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override product URLs (skip sitemaps).
      max_pages     — limits product URLs per sitemap (urls = max_pages * 50).
    """

    name = "jiomart"
    allowed_domains = ["jiomart.com", "www.jiomart.com"]

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 404, 429],
        # CurlCffi middleware intercepts HTTP requests and uses Chrome
        # TLS impersonation to bypass Akamai JA3 fingerprinting.
        # Priority 100 = runs before all other downloader middlewares.
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.spiders.jiomart_spider.JioMartCurlCffiMiddleware": 100,
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
        self._override_urls: list[str] = (
            [u.strip() for u in category_urls.split(",") if u.strip()]
            if category_urls
            else []
        )
        self._max_pages_override: int | None = int(max_pages) if max_pages else None

        # Compute URL limit per sitemap
        if self._max_pages_override is not None:
            self._urls_per_sitemap = self._max_pages_override * 50
        else:
            self._urls_per_sitemap = DEFAULT_URLS_PER_SITEMAP

        # Dedup — track seen SKU IDs
        self._seen_ids: set[str] = set()

        # Stats
        self._sitemaps_fetched: int = 0
        self._product_urls_found: int = 0
        self._product_pages_fetched: int = 0
        self._products_extracted: int = 0
        self._stale_urls: int = 0
        self._duplicates_skipped: int = 0

    # ------------------------------------------------------------------
    # Header override — Akamai bypass requires specific Chrome headers
    # ------------------------------------------------------------------

    def _make_headers(self) -> dict[str, str]:
        """Return JioMart-specific headers for Akamai bypass.

        The actual HTTP request is made by JioMartCurlCffiMiddleware
        using JIOMART_HEADERS with Chrome TLS impersonation.
        """
        return dict(JIOMART_HEADERS)

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        self.logger.info(
            f"JioMart spider finished ({reason}): "
            f"sitemaps={self._sitemaps_fetched}, "
            f"product_urls_found={self._product_urls_found}, "
            f"product_pages={self._product_pages_fetched}, "
            f"products_extracted={self._products_extracted}, "
            f"stale_404s={self._stale_urls}, "
            f"duplicates_skipped={self._duplicates_skipped}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Fetch the main sitemap index or override URLs."""
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

        # Override mode: directly scrape provided product URLs
        if self._override_urls:
            self.logger.info(
                f"Override mode: scraping {len(self._override_urls)} URLs directly"
            )
            for url in self._override_urls:
                yield scrapy.Request(
                    url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "category_slug": self._resolve_category_from_url(url),
                        "playwright": False,
                    },
                )
            return

        # Normal mode: start from sitemap index
        self.logger.info("Fetching sitemap index")
        yield scrapy.Request(
            SITEMAP_INDEX_URL,
            callback=self.parse_sitemap_index,
            errback=self.handle_error,
            headers=self._make_headers(),
            meta={"playwright": False},
        )

    # ------------------------------------------------------------------
    # Phase 1: Sitemap parsing
    # ------------------------------------------------------------------

    def parse_sitemap_index(self, response):
        """Parse the sitemap index XML and follow allowed sub-sitemaps."""
        if response.status in (403, 429):
            self.logger.error(
                f"Blocked ({response.status}) on sitemap index — cannot proceed"
            )
            return

        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            self.logger.error(f"Failed to parse sitemap index XML: {exc}")
            return

        # Extract <loc> URLs from sitemap index
        sitemap_urls = [
            loc.text.strip()
            for loc in root.findall(".//sm:sitemap/sm:loc", SITEMAP_NS)
            if loc.text
        ]

        # Fallback: try without namespace (some sitemaps don't use it)
        if not sitemap_urls:
            sitemap_urls = [
                loc.text.strip()
                for loc in root.iter()
                if loc.tag.endswith("loc") and loc.text
            ]

        self.logger.info(
            f"Found {len(sitemap_urls)} sub-sitemaps in index"
        )

        # Filter to allowed categories for v1
        for url in sitemap_urls:
            url_lower = url.lower()
            category_hint = None

            for pattern, cat_slug in ALLOWED_SITEMAPS.items():
                if pattern in url_lower:
                    category_hint = cat_slug
                    break

            if category_hint is None:
                self.logger.debug(f"Skipping sitemap (not in v1 scope): {url}")
                continue

            self.logger.info(f"Following sub-sitemap ({category_hint}): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_sitemap,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_hint": category_hint,
                    "playwright": False,
                },
                dont_filter=True,
            )

    def parse_sitemap(self, response):
        """Parse a sub-sitemap XML and extract product URLs."""
        self._sitemaps_fetched += 1

        if response.status in (403, 429):
            self.logger.warning(
                f"Blocked ({response.status}) on sitemap {response.url}"
            )
            return

        category_hint = response.meta.get("category_hint", "")

        try:
            root = ElementTree.fromstring(response.text)
        except ElementTree.ParseError as exc:
            self.logger.error(
                f"Failed to parse sitemap XML {response.url}: {exc}"
            )
            return

        # Extract all <loc> URLs
        all_urls = [
            loc.text.strip()
            for loc in root.findall(".//sm:url/sm:loc", SITEMAP_NS)
            if loc.text
        ]

        # Fallback: try without namespace
        if not all_urls:
            all_urls = [
                loc.text.strip()
                for loc in root.iter()
                if loc.tag.endswith("loc") and loc.text
            ]

        # Filter to product URLs only (pattern: /p/{vertical}/{slug}/{sku_id})
        product_urls = [
            url for url in all_urls
            if PRODUCT_URL_RE.search(url)
        ]

        self.logger.info(
            f"Sitemap {response.url}: "
            f"{len(all_urls)} total URLs, "
            f"{len(product_urls)} product URLs"
        )

        # Limit URLs per sitemap
        urls_to_process = product_urls[:self._urls_per_sitemap]
        self._product_urls_found += len(urls_to_process)

        product_count = 0
        for url in urls_to_process:
            # Extract SKU ID for dedup
            sku_match = SKU_ID_RE.search(url)
            if not sku_match:
                continue
            sku_id = sku_match.group(1)

            if sku_id in self._seen_ids:
                self._duplicates_skipped += 1
                continue
            self._seen_ids.add(sku_id)

            product_count += 1
            category_slug = self._resolve_category_from_url(url) or category_hint

            yield scrapy.Request(
                url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "sku_id": sku_id,
                    "playwright": False,
                },
            )

        self.logger.info(
            f"Queued {product_count} product pages from {response.url}"
        )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages (SSR HTML parsing)
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Parse SSR HTML product detail page for structured data."""
        self._product_pages_fetched += 1

        # Handle stale sitemap URLs gracefully
        if response.status == 404:
            self._stale_urls += 1
            self.logger.debug(f"Stale URL (404): {response.url}")
            return

        if response.status in (403, 429):
            self.logger.warning(
                f"Blocked ({response.status}) on {response.url}"
            )
            self.items_failed += 1
            return

        if response.status >= 400:
            self.logger.warning(
                f"Error {response.status} on {response.url}"
            )
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        sku_id = response.meta.get("sku_id")

        # Fallback SKU ID extraction from URL
        if not sku_id:
            sku_match = SKU_ID_RE.search(response.url)
            sku_id = sku_match.group(1) if sku_match else None

        if not sku_id:
            self.logger.warning(f"No SKU ID for {response.url} — skipping")
            self.items_failed += 1
            return

        item = self._extract_product(response, category_slug, sku_id)
        if item:
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
        else:
            self.logger.warning(
                f"Could not extract product data from {response.url}"
            )
            self.items_failed += 1

    def _extract_product(
        self, response, category_slug: str | None, sku_id: str,
    ) -> ProductItem | None:
        """Extract product data from JioMart SSR HTML.

        Data sources:
          1. HTML elements (product name, prices, specs table)
          2. Meta tags (og: properties)
          3. JSON-LD BreadcrumbList (for breadcrumbs only — no Product schema)
        """
        # === Title ===
        title = (
            response.css("h1.product-header-name::text").get()
            or response.css("h1::text").get()
            or response.css("meta[property='og:title']::attr(content)").get()
        )
        if not title or not title.strip():
            return None
        title = title.strip()

        # === Prices (rupees → paisa) ===
        selling_price = self._extract_selling_price(response)
        mrp = self._extract_mrp(response)

        # === Brand ===
        brand = (
            response.css(".product-info-brand a::text").get()
            or response.css(".brand-name::text").get()
            or response.css("[class*='brand'] a::text").get()
        )
        if brand:
            brand = brand.strip() or None

        # === Images ===
        images = self._extract_images(response)

        # === Rating ===
        rating = None
        rating_str = (
            response.css(".rating-value::text").get()
            or response.css("[class*='rating'] span::text").get()
        )
        if rating_str:
            try:
                val = Decimal(rating_str.strip())
                if 0 < val <= 5:
                    rating = val
            except (InvalidOperation, ValueError):
                pass

        # === Review count ===
        review_count = None
        review_str = response.css(
            "[class*='review-count']::text, "
            "[class*='rating-count']::text"
        ).get()
        if review_str:
            nums = re.findall(r"\d+", review_str)
            if nums:
                try:
                    review_count = int(nums[0])
                    if review_count == 0:
                        review_count = None
                except (ValueError, TypeError):
                    pass

        # === Seller ===
        seller_name = (
            response.css(".seller-name::text").get()
            or response.css("[class*='seller'] a::text").get()
            or response.css("[class*='sold-by'] span::text").get()
        )
        if seller_name:
            seller_name = seller_name.strip()

        # === Specifications ===
        specs = self._extract_specs(response)

        # === Description ===
        description = response.css(
            ".product-description::text, "
            "[class*='product-desc']::text, "
            "meta[property='og:description']::attr(content)"
        ).get()
        if description:
            description = description.strip()[:5000] or None

        # === Stock ===
        out_of_stock_el = response.css(
            ".out-of-stock, [class*='sold-out'], [class*='outofstock']"
        )
        add_to_cart = response.css(
            "button[class*='add-to-cart'], button[class*='addtocart']"
        )
        in_stock = len(out_of_stock_el) == 0 or len(add_to_cart) > 0

        # === Breadcrumbs ===
        breadcrumbs = self._extract_breadcrumbs(response)

        # === Category from breadcrumbs or URL ===
        if not category_slug and breadcrumbs:
            for crumb in breadcrumbs:
                crumb_lower = crumb.lower()
                for kw, slug in VERTICAL_CATEGORY_MAP.items():
                    if kw in crumb_lower:
                        category_slug = slug
                        break
                if category_slug:
                    break

        # === Metadata from specs ===
        manufacturer = (
            specs.get("Manufacturer")
            or specs.get("manufacturer")
            or brand
        )
        weight = (
            specs.get("Weight")
            or specs.get("Net Weight")
            or specs.get("weight")
        )
        dimensions = specs.get("Dimensions") or specs.get("dimensions")
        model_number = (
            specs.get("Model Number")
            or specs.get("Model Name")
            or specs.get("model")
        )
        warranty = specs.get("Warranty") or specs.get("warranty")
        country_of_origin = (
            specs.get("Country of Origin")
            or specs.get("Country Of Origin")
        )

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=sku_id,
            url=response.url,
            title=title,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name=seller_name or "JioMart",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="JioMart",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=str(warranty) if warranty else None,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=str(country_of_origin) if country_of_origin else None,
            manufacturer=str(manufacturer) if manufacturer else None,
            model_number=str(model_number) if model_number else None,
            weight=str(weight) if weight else None,
            dimensions=str(dimensions) if dimensions else None,
        )

    # ------------------------------------------------------------------
    # Price extraction
    # ------------------------------------------------------------------

    def _extract_selling_price(self, response) -> Decimal | None:
        """Extract the selling/offer price from HTML (rupees → paisa)."""
        price_str = (
            response.css(".selling-price::text").get()
            or response.css("[class*='selling-price']::text").get()
            or response.css("[class*='offer-price']::text").get()
            or response.css("[class*='final-price']::text").get()
            or response.css(".jm-heading-xxs::text").get()
        )

        # Fallback: look for ₹ symbol in price containers
        if not price_str:
            for text in response.css("[class*='price'] ::text").getall():
                if "₹" in text or "Rs" in text:
                    price_str = text
                    break

        return self._parse_price(price_str)

    def _extract_mrp(self, response) -> Decimal | None:
        """Extract the MRP (maximum retail price) from HTML (rupees → paisa)."""
        mrp_str = (
            response.css(".mrp-price::text").get()
            or response.css("[class*='mrp']::text").get()
            or response.css("[class*='strikethrough']::text").get()
            or response.css("del::text").get()
            or response.css(".original-price::text").get()
        )
        return self._parse_price(mrp_str)

    # ------------------------------------------------------------------
    # Image extraction
    # ------------------------------------------------------------------

    def _extract_images(self, response) -> list[str]:
        """Extract product images from various HTML sources."""
        images: list[str] = []
        seen: set[str] = set()

        def _add(url: str) -> None:
            if not url or url.startswith("data:"):
                return
            clean = url.split("?")[0]
            if clean.startswith("//"):
                clean = "https:" + clean
            if clean not in seen:
                seen.add(clean)
                images.append(clean)

        # Product gallery images
        for sel in (
            "img.product-image::attr(src)",
            "[class*='product-image'] img::attr(src)",
            "[class*='gallery'] img::attr(src)",
            ".pdp-image img::attr(src)",
            "img[class*='pdp']::attr(src)",
        ):
            for img in response.css(sel).getall():
                _add(img)

        # Lazy-loaded images (JioMart CDN: cdn.jiostore.online)
        for img in response.css("img[data-src]::attr(data-src)").getall():
            if "jiomart" in img or "jiostore" in img or "cdn" in img:
                _add(img)

        # OG image fallback
        if not images:
            og = response.css("meta[property='og:image']::attr(content)").get()
            if og:
                _add(og)

        return images

    # ------------------------------------------------------------------
    # Specification extraction
    # ------------------------------------------------------------------

    def _extract_specs(self, response) -> dict[str, str]:
        """Extract product specifications from detail page."""
        specs: dict[str, str] = {}

        # Primary: table-based specs (common on JioMart PDPs)
        for row in response.css(
            ".specification-row, "
            ".spec-row, "
            "[class*='spec'] tr, "
            "[class*='product-info'] tr, "
            ".product-detail-row"
        ):
            label = row.css(
                "td:first-child::text, "
                "th::text, "
                ".spec-label::text, "
                ".spec-key::text"
            ).get()
            value = row.css(
                "td:last-child::text, "
                ".spec-value::text, "
                ".spec-desc::text"
            ).get()
            if label and value and label.strip() and value.strip():
                specs[label.strip()] = value.strip()

        # Fallback: key-value pairs in divs
        for row in response.css("[class*='attribute'], [class*='detail-row']"):
            label = row.css(
                "[class*='label']::text, "
                "[class*='key']::text, "
                "span:first-child::text"
            ).get()
            value = row.css(
                "[class*='value']::text, "
                "span:last-child::text"
            ).get()
            if (
                label and value
                and label.strip() and value.strip()
                and label.strip() != value.strip()
            ):
                specs[label.strip()] = value.strip()

        return specs

    # ------------------------------------------------------------------
    # Breadcrumb extraction
    # ------------------------------------------------------------------

    def _extract_breadcrumbs(self, response) -> list[str]:
        """Extract breadcrumb trail from JSON-LD or HTML."""
        breadcrumbs: list[str] = []

        # Try JSON-LD BreadcrumbList
        for script in response.css(
            'script[type="application/ld+json"]::text'
        ).getall():
            try:
                ld_data = json.loads(script)
                if isinstance(ld_data, list):
                    for item in ld_data:
                        if isinstance(item, dict) and item.get("@type") == "BreadcrumbList":
                            ld_data = item
                            break
                if (
                    isinstance(ld_data, dict)
                    and ld_data.get("@type") == "BreadcrumbList"
                ):
                    for element in ld_data.get("itemListElement", []):
                        name = element.get("name", "").strip()
                        if name:
                            breadcrumbs.append(name)
                    if breadcrumbs:
                        return breadcrumbs
            except (json.JSONDecodeError, ValueError):
                continue

        # Fallback: HTML breadcrumbs
        for bc in response.css(
            ".breadcrumb a::text, "
            "[class*='breadcrumb'] a::text, "
            "nav[aria-label='breadcrumb'] a::text"
        ).getall():
            text = bc.strip()
            if text:
                breadcrumbs.append(text)

        return breadcrumbs

    # ------------------------------------------------------------------
    # URL helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract category slug from JioMart product URL path.

        URL pattern: /p/{vertical}/{slug}/{sku_id}
        """
        match = re.search(r"/p/([^/]+)/", url)
        if not match:
            return None
        vertical = match.group(1).lower()
        return VERTICAL_CATEGORY_MAP.get(vertical)

    # ------------------------------------------------------------------
    # Price helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_price(price_str: str | None) -> Decimal | None:
        """Parse a price string (rupees) to Decimal in paisa."""
        if not price_str:
            return None
        match = PRICE_RE.search(str(price_str).strip())
        if not match:
            return None
        try:
            rupees = Decimal(match.group().replace(",", ""))
            if rupees <= 0:
                return None
            return rupees * 100  # Convert to paisa
        except (InvalidOperation, ValueError):
            return None
