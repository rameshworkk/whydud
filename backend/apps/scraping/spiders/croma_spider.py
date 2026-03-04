"""Croma spider — HTTP-only with curl_cffi TLS impersonation.

Architecture:
  Croma runs React SSR backed by SAP Hybris. Akamai Bot Manager blocks
  standard HTTP clients (403) but curl_cffi with Chrome TLS impersonation
  bypasses it completely.

  Strategy:
    Phase 1 (Listing): HTTP GET category pages → parse __INITIAL_DATA__
      plpReducer.plpData.products for product URLs + basic data.
    Phase 2 (Detail): HTTP GET product pages → parse __INITIAL_DATA__
      pdpReducer.pdpData for full specs, images, description.
      Price from pdpPriceReducer.pdpPriceData.

  NO Playwright needed — HTTP only via curl_cffi.

  All prices in RUPEES — converted to paisa (* 100) before yielding.

  IMPORTANT: __INITIAL_DATA__ JSON contains JavaScript `undefined` values
  that must be replaced with `null` before JSON.loads().

URL patterns:
  Category: /{category-path}/c/{numeric_id}?page={n}
  Product:  /{product-slug}/p/{product_code}
"""
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

MARKETPLACE_SLUG = "croma"

PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")
PRODUCT_CODE_RE = re.compile(r"/p/(\d+)")

# Chrome/131 headers for Akamai bypass
CROMA_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
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

class CromaCurlCffiMiddleware:
    """Scrapy downloader middleware that uses curl_cffi for Croma requests.

    Akamai Bot Manager fingerprints TLS handshakes (JA3/JA4).
    Python's ssl module has a distinct fingerprint that's blocked (403).
    curl_cffi wraps libcurl and impersonates Chrome's TLS handshake.
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
        try:
            self._session.close()
        except Exception:
            pass

    def process_request(self, request, spider):
        """Intercept request and fetch via curl_cffi."""
        if request.meta.get("playwright"):
            return None
        if "croma.com" not in request.url:
            return None

        self._request_count += 1

        try:
            resp = self._session.get(
                request.url,
                headers=dict(CROMA_HEADERS),
                timeout=60,
                allow_redirects=True,
            )

            # Strip Content-Encoding — curl_cffi already decompresses
            resp_headers = {
                k: v for k, v in resp.headers.items()
                if k.lower() != "content-encoding"
            }

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


# ---------------------------------------------------------------------------
# Category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "mobile-phones": "smartphones",
    "mobile-accessories": "smartphones",
    "laptops": "laptops",
    "tablets": "tablets",
    "monitors": "laptops",
    "printers": "laptops",
    "networking": "laptops",
    "storage-devices": "laptops",
    "led-tvs": "televisions",
    "projectors": "televisions",
    "streaming-devices": "televisions",
    "headphones": "audio",
    "earphones": "audio",
    "bluetooth-portable-speakers": "audio",
    "soundbars-home-theatre": "audio",
    "party-speakers": "audio",
    "smart-watches": "smartwatches",
    "digital-cameras": "cameras",
    "action-cameras": "cameras",
    "refrigerators": "refrigerators",
    "washing-machines": "washing-machines",
    "air-conditioners": "air-conditioners",
    "microwave-ovens": "appliances",
    "dishwashers": "appliances",
    "water-heaters": "appliances",
    "air-purifiers": "appliances",
    "water-purifiers": "appliances",
    "vacuum-cleaners": "appliances",
    "fans": "appliances",
    "mixer-grinders": "kitchen-tools",
    "air-fryer": "kitchen-tools",
    "coffee-machines": "kitchen-tools",
    "induction-cooktops": "kitchen-tools",
    "electric-kettles": "kitchen-tools",
    "oven-toaster-grills": "kitchen-tools",
    "gas-stoves": "kitchen-tools",
    "trimmers-shavers": "grooming",
    "hair-care": "grooming",
    "gaming-consoles": "gaming",
    "gaming-accessories": "gaming",
}

# ---------------------------------------------------------------------------
# Seed category URLs — (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 20
_STD = 10

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # Smartphones
    ("https://www.croma.com/phones-wearables/mobile-phones/c/22", _TOP),
    ("https://www.croma.com/phones-wearables/mobile-accessories/c/23", _STD),
    # Laptops & Computers
    ("https://www.croma.com/computers-tablets/laptops/c/30", _TOP),
    ("https://www.croma.com/computers-tablets/tablets/c/31", _STD),
    ("https://www.croma.com/computers-tablets/monitors/c/474", _STD),
    ("https://www.croma.com/computers-tablets/printers-scanners/c/35", _STD),
    ("https://www.croma.com/computers-tablets/networking/c/33", _STD),
    ("https://www.croma.com/computers-tablets/storage-devices/c/34", _STD),
    # TVs
    ("https://www.croma.com/televisions-accessories/led-tvs/c/392", _TOP),
    ("https://www.croma.com/televisions-accessories/projectors/c/14", _STD),
    ("https://www.croma.com/televisions-accessories/streaming-devices/c/395", _STD),
    # Audio
    ("https://www.croma.com/audio-video/headphones-earphones/c/17", _TOP),
    ("https://www.croma.com/audio-video/bluetooth-portable-speakers/c/459", _TOP),
    ("https://www.croma.com/audio-video/soundbars-home-theatre/c/16", _STD),
    ("https://www.croma.com/audio-video/party-speakers/c/461", _STD),
    # Wearables
    ("https://www.croma.com/phones-wearables/smart-watches-bands/c/463", _TOP),
    # Cameras
    ("https://www.croma.com/cameras-accessories/digital-cameras/c/36", _STD),
    ("https://www.croma.com/cameras-accessories/action-cameras/c/40", _STD),
    # Large Appliances
    ("https://www.croma.com/home-appliances/refrigerators/c/5", _TOP),
    ("https://www.croma.com/home-appliances/washing-machines/c/7", _TOP),
    ("https://www.croma.com/home-appliances/air-conditioners/c/3", _TOP),
    ("https://www.croma.com/home-appliances/microwave-ovens/c/475", _STD),
    ("https://www.croma.com/home-appliances/dishwashers/c/472", _STD),
    ("https://www.croma.com/home-appliances/water-heaters/c/476", _STD),
    # Small Appliances
    ("https://www.croma.com/home-appliances/air-purifiers/c/430", _STD),
    ("https://www.croma.com/home-appliances/water-purifiers/c/470", _STD),
    ("https://www.croma.com/home-appliances/vacuum-cleaners/c/471", _STD),
    ("https://www.croma.com/home-appliances/fans/c/477", _STD),
    # Kitchen Appliances
    ("https://www.croma.com/kitchen-appliances/mixer-grinders-juicers/c/46", _STD),
    ("https://www.croma.com/kitchen-appliances/air-fryer/c/487", _STD),
    ("https://www.croma.com/kitchen-appliances/coffee-machines/c/51", _STD),
    ("https://www.croma.com/kitchen-appliances/induction-cooktops/c/489", _STD),
    ("https://www.croma.com/kitchen-appliances/electric-kettles/c/488", _STD),
    ("https://www.croma.com/kitchen-appliances/oven-toaster-grills/c/48", _STD),
    ("https://www.croma.com/kitchen-appliances/gas-stoves-hobs/c/490", _STD),
    # Personal Care
    ("https://www.croma.com/personal-care/trimmers-shavers/c/62", _STD),
    ("https://www.croma.com/personal-care/hair-care/c/479", _STD),
    # Gaming
    ("https://www.croma.com/gaming/gaming-consoles/c/458", _STD),
    ("https://www.croma.com/gaming/gaming-accessories/c/482", _STD),
]

MAX_LISTING_PAGES = 5
QUICK_MODE_CATEGORIES = 8

# Regex to fix JS `undefined` in __INITIAL_DATA__ JSON
_UNDEFINED_RE = re.compile(r"\bundefined\b")


class CromaSpider(BaseWhydudSpider):
    """Scrapes Croma.com — HTTP-only with curl_cffi TLS impersonation.

    Extracts product data from SSR __INITIAL_DATA__ Redux store.
    Phase 1: Category listings → plpReducer.plpData.products
    Phase 2: Product detail pages → pdpReducer.pdpData + pdpPriceReducer

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "croma"
    allowed_domains = ["croma.com", "www.croma.com"]

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429, 503],
        # Register curl_cffi middleware at priority 100 (before all others)
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.spiders.croma_spider.CromaCurlCffiMiddleware": 100,
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
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}

        # Stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._listing_extractions: int = 0
        self._pdp_extractions: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Croma spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"listing_extractions={self._listing_extractions}, "
            f"pdp_extractions={self._pdp_extractions}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit HTTP requests for category listing pages."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}")
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        url_pairs = self._load_urls()

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

        self.logger.info(f"Queued {len(url_pairs)} categories (HTTP + curl_cffi)")

    def _load_urls(self) -> list[tuple[str, int]]:
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]

        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                self.logger.info(
                    f"Quick mode: {QUICK_MODE_CATEGORIES} categories, "
                    f"max_pages={self._max_pages_override}"
                )
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[:QUICK_MODE_CATEGORIES]
                ]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # __INITIAL_DATA__ extraction
    # ------------------------------------------------------------------

    def _extract_initial_data(self, response) -> dict | None:
        """Extract and parse window.__INITIAL_DATA__ from page HTML.

        The JSON contains JavaScript `undefined` values which must be
        replaced with `null` before parsing.
        """
        for script_text in response.css("script::text").getall():
            if "window.__INITIAL_DATA__" not in script_text:
                continue

            idx = script_text.index("window.__INITIAL_DATA__")
            eq_idx = script_text.index("=", idx)
            json_start = eq_idx + 1

            # Skip whitespace
            while json_start < len(script_text) and script_text[json_start] in " \t\n\r":
                json_start += 1

            raw = script_text[json_start:].rstrip().rstrip(";")
            fixed = _UNDEFINED_RE.sub("null", raw)

            try:
                return json.loads(fixed)
            except (json.JSONDecodeError, ValueError) as exc:
                self.logger.warning(f"Failed to parse __INITIAL_DATA__: {exc}")
                return None

        return None

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from category listing page via __INITIAL_DATA__."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        data = self._extract_initial_data(response)
        if not data:
            self.logger.warning(f"No __INITIAL_DATA__ on {response.url}")
            return

        plp_data = data.get("plpReducer", {}).get("plpData", {})
        products = plp_data.get("products", [])

        if not products:
            self.logger.warning(f"No products in __INITIAL_DATA__ on {response.url}")
            return

        self.logger.info(f"Found {len(products)} products on {response.url}")

        for prod in products:
            prod_url = prod.get("url")
            code = prod.get("code")
            if not prod_url and not code:
                continue

            full_url = response.urljoin(prod_url or f"/p/{code}")

            yield scrapy.Request(
                full_url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "listing_data": prod,
                },
            )

        # Pagination
        pagination = plp_data.get("pagination", {})
        current_page = pagination.get("currentPage", 0)
        total_pages = pagination.get("totalPages", 1)

        base_url = response.url.split("?page=")[0].split("&page=")[0]
        max_for_cat = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)
        pages_so_far = self._pages_followed.get(base_url, 1)

        if current_page + 1 < total_pages and pages_so_far < max_for_cat:
            next_page_num = current_page + 1
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page={next_page_num}"
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
        """Extract product data from detail page via __INITIAL_DATA__."""
        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        code_match = PRODUCT_CODE_RE.search(response.url)
        external_id = code_match.group(1) if code_match else None

        # Strategy 1: __INITIAL_DATA__ pdpReducer (full data)
        data = self._extract_initial_data(response)
        if data:
            pdp_data = data.get("pdpReducer", {}).get("pdpData", {})
            price_data = data.get("pdpPriceReducer", {}).get("pdpPriceData", {})

            if pdp_data and pdp_data.get("name"):
                item = self._build_from_pdp(
                    pdp_data, price_data, response.url, category_slug, external_id,
                )
                if item:
                    self._pdp_extractions += 1
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: Listing data fallback (less detail but usable)
        if listing_data:
            item = self._build_from_listing(
                listing_data, response.url, category_slug, external_id,
            )
            if item:
                self._listing_extractions += 1
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # Item builders
    # ------------------------------------------------------------------

    def _build_from_pdp(
        self,
        pdp: dict,
        price_data: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from pdpReducer.pdpData + pdpPriceReducer."""
        name = pdp.get("name")
        if not name:
            return None

        code = external_id or str(pdp.get("code", ""))
        if not code:
            return None

        # Prices from pdpPriceReducer (values are strings in rupees)
        selling_price = self._parse_price(
            price_data.get("sellingPrice", {}).get("value")
        )
        mrp = self._parse_price(
            price_data.get("mrp", {}).get("value")
        )

        # Fallback: price from pdpData itself
        if not selling_price:
            pdp_price = pdp.get("price")
            if isinstance(pdp_price, dict):
                selling_price = self._parse_price(pdp_price.get("value"))
            else:
                selling_price = self._parse_price(pdp_price)
        if not mrp:
            pdp_mrp = pdp.get("mrp")
            if isinstance(pdp_mrp, dict):
                mrp = self._parse_price(pdp_mrp.get("value"))
            else:
                mrp = self._parse_price(pdp_mrp)

        # Images from imageInfo array
        images = []
        for img in pdp.get("imageInfo") or []:
            img_url = img.get("url", "")
            if img_url:
                images.append(img_url)

        # Specs from classifications
        specs = {}
        for group in pdp.get("classifications") or []:
            for feature in group.get("features") or []:
                key = feature.get("name", "")
                vals = feature.get("featureValues") or []
                val = vals[0].get("value", "") if vals else feature.get("value", "")
                if key and val:
                    specs[key] = val

        brand = pdp.get("manufacturer") or specs.get("Brand")

        # Rating
        rating = None
        review_count = None
        rating_val = pdp.get("finalReviewRating") or pdp.get("averageRating")
        if rating_val and str(rating_val) not in ("0", "0.0", ""):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = pdp.get("finalReviewRatingCount") or pdp.get("numberOfReviews")
        if count_val and str(count_val) not in ("0", ""):
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Key features as about bullets
        about_bullets = []
        for i in range(1, 7):
            feat = pdp.get(f"keyFeature{i}")
            if feat:
                about_bullets.append(feat)

        # Description
        description = pdp.get("description") or pdp.get("summary")

        # Warranty
        warranty = pdp.get("standardWarranty")
        if warranty:
            warranty = f"{warranty} months" if warranty.isdigit() else warranty

        # Breadcrumbs
        breadcrumbs = [
            bc.get("name") for bc in pdp.get("pdpBreadcrumbs") or []
            if bc.get("name")
        ]

        # Variants
        variant_options = []
        for v in pdp.get("variantInfo") or []:
            if v.get("name") and v.get("value"):
                variant_options.append({"name": v["name"], "value": v["value"]})

        # Category from URL if not set
        if not category_slug:
            category_slug = self._resolve_category_from_url(url)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=code,
            url=url,
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
            in_stock=True,
            fulfilled_by="Croma",
            category_slug=category_slug,
            about_bullets=about_bullets,
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=warranty,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=variant_options,
            country_of_origin=specs.get("Country of Origin"),
            manufacturer=brand,
            model_number=specs.get("Model Number") or specs.get("Model Name"),
            weight=specs.get("Product Weight") or specs.get("Weight"),
            dimensions=specs.get("Dimensions In CM (WxDxH)") or specs.get("Product Dimensions"),
        )

    def _build_from_listing(
        self,
        prod: dict,
        url: str,
        category_slug: str | None,
        external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from listing page data (less detailed)."""
        name = prod.get("name")
        if not name:
            return None

        code = external_id or str(prod.get("code", ""))
        if not code:
            return None

        # Price from listing — mrp and price are {value, formattedValue} dicts
        selling_price = None
        mrp_val = None
        price_field = prod.get("price")
        if isinstance(price_field, dict):
            selling_price = self._parse_price(price_field.get("value"))
        else:
            selling_price = self._parse_price(price_field)

        mrp_field = prod.get("mrp")
        if isinstance(mrp_field, dict):
            mrp_val = self._parse_price(mrp_field.get("value"))
        else:
            mrp_val = self._parse_price(mrp_field)

        # Listing image
        images = []
        plp_img = prod.get("plpImage")
        if plp_img:
            images.append(plp_img)

        rating = None
        review_count = None
        rating_val = prod.get("finalReviewRating") or prod.get("averageRating")
        if rating_val and str(rating_val) not in ("0", "0.0", ""):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = prod.get("finalReviewRatingCount") or prod.get("numberOfReviews")
        if count_val and str(count_val) not in ("0", ""):
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        warranty = prod.get("standardWarranty")
        if isinstance(warranty, list) and warranty:
            warranty = f"{warranty[0]} months"
        elif warranty:
            warranty = f"{warranty} months" if str(warranty).isdigit() else str(warranty)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=code,
            url=url,
            title=name,
            brand=prod.get("manufacturer"),
            price=selling_price,
            mrp=mrp_val,
            images=images,
            rating=rating,
            review_count=review_count,
            specs={},
            seller_name="Croma",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Croma",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=prod.get("summary"),
            warranty=warranty,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=[],
            variant_options=[],
            country_of_origin=None,
            manufacturer=prod.get("manufacturer"),
            model_number=None,
            weight=None,
            dimensions=None,
        )

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value to Decimal in paisa (rupees x 100)."""
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
        """Detect Akamai block or challenge page."""
        if response.status in (403, 429):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        if len(response.text) < 500:
            return True
        return False

    def _resolve_category_from_url(self, url: str) -> str | None:
        """Extract whydud category slug from URL path."""
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None
