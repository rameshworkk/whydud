"""FirstCry spider — HTTP-only scraper for baby & kids products.

Architecture:
  Phase 1 (Listing): Search-based discovery via /search?q={query}.
    FirstCry redirects search queries to category listing pages with SSR HTML.
    20 product cards per page. Pagination via ?page=N query param.
    Product links extracted from href attributes (//www.firstcry.com/.../PID/product-detail).

  Phase 2 (Detail): HTTP GET product-detail pages. Extracts product data from
    the embedded `CurrentProductDetailJSON` JavaScript variable in <script> tags.
    Also extracts avg_rating, totalreview, cat_url, scat_url from JS vars.

  NO Playwright needed — HTTP only via curl_cffi with Chrome TLS impersonation.
  Server is Apache/OpenSSL (no Cloudflare/Akamai), but curl_cffi is used for
  TLS safety and consistency with other spiders.

  Prices on FirstCry are in RUPEES (not paisa). Spider converts to paisa (* 100).

  CRITICAL: FirstCry is a baby/kids platform. Every product has an age group
  (e.g., "0-6 Months", "2-4 Years"). This is extracted from hashAgeG in
  CurrentProductDetailJSON and stored in specs.age_group.

URL patterns:
  Search: /search?q={query} → redirects to /category-name/cat-id/subcat-id?...
  Product: /{brand}/{slug}/{product-id}/product-detail
  Images: //cdn.fcglcdn.com/brainbees/images/products/{size}/{id}{letter}.webp

Data source (product page):
  CurrentProductDetailJSON = {
    "variant_id": {
      "pn": "Product Name",
      "mrp": 2299,            // MRP in rupees
      "Dis": 67.04,           // Discount %
      "pd": "Description...",
      "Img": "id_a.jpg;id_b.jpg;...",  // Semicolon-separated image filenames
      "hashAgeG": ["0#0-3 Months", ...],  // Age groups
      "hashCols": ["10#Multi Color"],     // Color options
      "sz": "L 6.5 x B 4.5 ft",          // Size
      "pid": 18544598,        // Variant product ID
      "w": "",                // Weight
      "warranty": "",
      ...
    }
  }
  Also: avg_rating="4.2", totalreview="618" as separate JS vars.
"""
import json
import logging
import random
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

MARKETPLACE_SLUG = "firstcry"

# Chrome/131 headers — Apache server, no aggressive anti-bot
FIRSTCRY_HEADERS = {
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

PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

# Extract product ID from product-detail URL: /brand/slug/PRODUCT_ID/product-detail
PRODUCT_ID_RE = re.compile(r"/(\d+)/product-detail")

# CDN base for product images
IMAGE_CDN = "https://cdn.fcglcdn.com/brainbees/images/products/438x531/"


# ===================================================================
# CurlCffi downloader middleware — Chrome TLS impersonation
# ===================================================================

class FirstCryCurlCffiMiddleware:
    """Scrapy downloader middleware using curl_cffi for FirstCry requests.

    FirstCry runs on Apache/OpenSSL which doesn't have aggressive TLS
    fingerprinting, but we use curl_cffi for consistency and to avoid
    any future anti-bot additions.
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
        if "firstcry.com" not in request.url:
            return None

        self._request_count += 1

        try:
            resp = self._session.get(
                request.url,
                headers=dict(FIRSTCRY_HEADERS),
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
# Search queries — baby/kids product categories
# Format: (query, whydud_category_slug)
# ---------------------------------------------------------------------------

SEED_SEARCH_QUERIES: list[tuple[str, str]] = [
    # Diapers & Baby Care
    ("baby diapers", "baby-care"),
    ("baby wipes", "baby-care"),
    ("baby lotion oil powder", "baby-care"),
    ("baby bath soap shampoo", "baby-care"),
    # Feeding
    ("baby feeding bottles", "baby-feeding"),
    ("breast pumps", "baby-feeding"),
    ("baby food cereal", "baby-feeding"),
    ("sippy cups", "baby-feeding"),
    # Clothing
    ("baby clothing newborn", "baby-clothing"),
    ("kids clothing boys", "kids-clothing"),
    ("kids clothing girls", "kids-clothing"),
    ("baby rompers bodysuit", "baby-clothing"),
    # Toys
    ("baby toys", "toys"),
    ("educational toys kids", "toys"),
    ("soft toys plush", "toys"),
    ("outdoor toys", "toys"),
    # Gear & Nursery
    ("baby strollers prams", "baby-gear"),
    ("baby car seats", "baby-gear"),
    ("baby cribs beds", "nursery"),
    ("baby carriers", "baby-gear"),
    # Footwear
    ("kids shoes", "kids-footwear"),
    ("baby booties", "kids-footwear"),
    # School
    ("school bags kids", "school-supplies"),
    ("kids water bottles lunch box", "school-supplies"),
]

MAX_LISTING_PAGES = 5
QUICK_MODE_QUERIES = 4


class FirstCrySpider(BaseWhydudSpider):
    """Scrapes FirstCry.com — India's largest baby & kids marketplace.

    HTTP-only spider — NO Playwright. Uses curl_cffi with Chrome/131 TLS
    impersonation (Apache server, minimal anti-bot).

    Search-based discovery: /search?q={query} → SSR listing pages.
    Product data from embedded CurrentProductDetailJSON JavaScript variable.

    CRITICAL: Extracts age_group for every product (baby/kids specific).

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs (product-detail or search).
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "firstcry"
    allowed_domains = ["firstcry.com", "www.firstcry.com"]

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
        "RETRY_TIMES": 3,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429, 404],
        "DOWNLOADER_MIDDLEWARES": {
            "scrapy.downloadermiddlewares.useragent.UserAgentMiddleware": None,
            "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
            "apps.scraping.spiders.firstcry_spider.FirstCryCurlCffiMiddleware": 100,
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
            f"FirstCry spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_pages={self._product_pages_scraped}, "
            f"products_ok={self._products_extracted} ({rate:.0f}%), "
            f"duplicates_skipped={self._duplicates_skipped}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit HTTP requests for search-based listing pages."""
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, "
                    f"marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        queries = self._load_queries()
        random.shuffle(queries)

        for query, cat_slug in queries:
            url = f"https://www.firstcry.com/search?q={query.replace(' ', '+')}"
            self.logger.info(f"Queuing search: {query} ({cat_slug})")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": cat_slug,
                    "search_query": query,
                    "playwright": False,
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(queries)} search queries (HTTP-only)")

    def _load_queries(self) -> list[tuple[str, str]]:
        """Resolve the (query, category_slug) list to crawl."""
        if self._category_urls:
            return [
                (u, "baby-care") for u in self._category_urls
            ]

        max_pages = self._max_pages_override
        if max_pages is not None and max_pages <= 2:
            self.logger.info(
                f"Quick mode: {QUICK_MODE_QUERIES} queries, "
                f"max_pages={max_pages}"
            )
            return SEED_SEARCH_QUERIES[:QUICK_MODE_QUERIES]

        return list(SEED_SEARCH_QUERIES)

    def _make_headers(self) -> dict[str, str]:
        """Return FirstCry-specific headers."""
        return dict(FIRSTCRY_HEADERS)

    # ------------------------------------------------------------------
    # Phase 1: Listing pages (search results)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from search result listing page.

        Products are in SSR HTML inside <div class="li_inner_block listingpg-{PID}">
        with links to //www.firstcry.com/{brand}/{slug}/{PID}/product-detail.
        20 products per page.
        """
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(
                f"Blocked ({response.status}) on listing {response.url}"
            )
            return

        if response.status == 404:
            self.logger.warning(f"404 on search {response.url}")
            return

        category_slug = response.meta.get("category_slug")

        # Extract product links from HTML
        # Pattern: href='//www.firstcry.com/brand/slug/PID/product-detail'
        raw_links = response.css(
            "div.li_inner_block a[href*='/product-detail']::attr(href)"
        ).getall()

        # Deduplicate and build full URLs
        seen_on_page: set[str] = set()
        product_count = 0

        for href in raw_links:
            # Normalize URL
            if href.startswith("//"):
                href = "https:" + href
            elif href.startswith("/"):
                href = "https://www.firstcry.com" + href

            # Extract product ID
            id_match = PRODUCT_ID_RE.search(href)
            if not id_match:
                continue
            pid = id_match.group(1)

            # Skip already seen on this page (multiple links per card)
            if pid in seen_on_page:
                continue
            seen_on_page.add(pid)

            # Global dedup
            if pid in self._seen_ids:
                self._duplicates_skipped += 1
                continue
            self._seen_ids.add(pid)

            product_count += 1

            yield scrapy.Request(
                href,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "external_id": pid,
                    "playwright": False,
                },
            )

        self.logger.info(
            f"Listing page: {product_count} new products from {response.url}"
        )

        if product_count == 0:
            return

        # Pagination
        max_pages = self._max_pages_override or MAX_LISTING_PAGES
        base_url = response.url.split("&page=")[0].split("?page=")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)

        if pages_so_far < max_pages:
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
                    "search_query": response.meta.get("search_query"),
                    "playwright": False,
                },
                dont_filter=True,
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page.

        Primary: CurrentProductDetailJSON embedded JS variable.
        Also extracts: avg_rating, totalreview, cat_url, scat_url.
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
        external_id = response.meta.get("external_id")

        if not external_id:
            id_match = PRODUCT_ID_RE.search(response.url)
            external_id = id_match.group(1) if id_match else None

        html = response.text

        # Extract CurrentProductDetailJSON
        product_json = self._extract_product_json(html)
        if not product_json:
            self.logger.warning(
                f"No CurrentProductDetailJSON on {response.url}"
            )
            self.items_failed += 1
            return

        # Extract ratings from separate JS variables
        avg_rating = self._extract_js_var(html, "avg_rating")
        total_review = self._extract_js_var(html, "totalreview")
        cat_url = self._extract_js_var(html, "cat_url")
        scat_url = self._extract_js_var(html, "scat_url")

        # CurrentProductDetailJSON has variant IDs as keys — use the first variant
        variants = list(product_json.values())
        if not variants:
            self.logger.warning(f"Empty product JSON on {response.url}")
            self.items_failed += 1
            return

        variant = variants[0]
        if not isinstance(variant, dict):
            self.items_failed += 1
            return

        item = self._build_product_item(
            variant=variant,
            url=response.url,
            external_id=external_id,
            category_slug=category_slug,
            avg_rating=avg_rating,
            total_review=total_review,
            cat_url=cat_url,
            scat_url=scat_url,
        )

        if item:
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
        else:
            self.items_failed += 1

    # ------------------------------------------------------------------
    # JS variable extraction
    # ------------------------------------------------------------------

    def _extract_product_json(self, html: str) -> dict | None:
        """Extract CurrentProductDetailJSON from embedded <script> tag.

        The variable is assigned as:
          CurrentProductDetailJSON = { "variant_id": { ... }, ... }
        """
        marker = "CurrentProductDetailJSON="
        idx = html.find(marker)
        if idx == -1:
            # Try with spaces
            marker = "CurrentProductDetailJSON ="
            idx = html.find(marker)
            if idx == -1:
                return None

        # Find the opening brace
        brace_start = html.find("{", idx)
        if brace_start == -1:
            return None

        try:
            decoder = json.JSONDecoder()
            obj, _ = decoder.raw_decode(html, brace_start)
            return obj if isinstance(obj, dict) else None
        except (json.JSONDecodeError, ValueError) as exc:
            self.logger.debug(f"JSON parse error for CurrentProductDetailJSON: {exc}")
            return None

    def _extract_js_var(self, html: str, var_name: str) -> str | None:
        """Extract a JavaScript variable value like: var_name="value" or var_name='value'."""
        # Match: var_name="value" or var_name='value'
        pattern = re.compile(
            rf'{var_name}\s*=\s*["\']([^"\']*)["\']'
        )
        match = pattern.search(html)
        if match:
            val = match.group(1).strip()
            return val if val else None
        return None

    # ------------------------------------------------------------------
    # Item builder
    # ------------------------------------------------------------------

    def _build_product_item(
        self,
        variant: dict,
        url: str,
        external_id: str | None,
        category_slug: str | None,
        avg_rating: str | None,
        total_review: str | None,
        cat_url: str | None,
        scat_url: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from a CurrentProductDetailJSON variant entry."""
        title = variant.get("pn", "").strip()
        if not title:
            return None

        pid = external_id or str(variant.get("pid", ""))
        if not pid:
            return None

        # Prices — MRP in rupees, convert to paisa
        mrp = self._parse_price(variant.get("mrp"))
        discount_pct = variant.get("Dis", 0)

        # Selling price = MRP * (1 - discount/100)
        selling_price = None
        if mrp is not None and discount_pct:
            try:
                discount = Decimal(str(discount_pct))
                selling_price = (mrp * (100 - discount) / 100).quantize(Decimal("1"))
            except (InvalidOperation, ValueError):
                selling_price = mrp
        elif mrp is not None:
            selling_price = mrp

        # Description
        description = variant.get("pd", "")
        if description:
            description = re.sub(r"<[^>]+>", " ", str(description))
            description = re.sub(r"\s+", " ", description).strip()[:5000]
        else:
            description = None

        # Images from Img field (semicolon-separated filenames)
        images = self._extract_images(variant)

        # Age groups (CRITICAL for baby/kids products)
        age_groups = self._extract_age_groups(variant)

        # Colors
        colors = self._extract_colors(variant)

        # Size
        size = variant.get("sz", "").strip() or None

        # Rating
        rating = None
        review_count = None
        if avg_rating:
            try:
                rating = Decimal(avg_rating)
                if rating <= 0:
                    rating = None
            except (InvalidOperation, ValueError):
                pass
        if total_review:
            try:
                review_count = int(total_review)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = variant.get("qty", 0) > 0

        # Warranty
        warranty = variant.get("warranty", "").strip() or None

        # Weight
        weight = variant.get("w", "").strip() or None

        # Build specs
        specs: dict[str, str] = {}
        if age_groups:
            specs["age_group"] = ", ".join(age_groups)
        if colors:
            specs["colors_available"] = ", ".join(colors)
        if size:
            specs["size"] = size
        if variant.get("Bestseller") == "1":
            specs["bestseller"] = "Yes"

        product_type = variant.get("ProductStyle", "").strip()
        if product_type:
            specs["product_type"] = product_type

        # Breadcrumbs from cat_url and scat_url
        breadcrumbs = self._build_breadcrumbs(cat_url, scat_url)

        # Category inference from breadcrumbs if not provided
        if not category_slug and breadcrumbs:
            category_slug = self._infer_category(breadcrumbs)

        # Variant options
        variant_options = []
        if colors and len(colors) > 1:
            variant_options.append({"name": "Color", "values": colors})
        if size:
            variant_options.append({"name": "Size", "values": [size]})

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=title,
            brand=self._extract_brand_from_url(url),
            price=selling_price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name="FirstCry",
            seller_rating=None,
            in_stock=in_stock,
            fulfilled_by="FirstCry",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=description,
            warranty=warranty,
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=variant_options,
            country_of_origin=None,
            manufacturer=self._extract_brand_from_url(url),
            model_number=None,
            weight=weight,
            dimensions=None,
        )

    # ------------------------------------------------------------------
    # Extraction helpers
    # ------------------------------------------------------------------

    def _extract_images(self, variant: dict) -> list[str]:
        """Extract product images from Img field.

        Img is a semicolon-separated list of filenames like:
        "16865160a.jpg;16865160b.jpg;PDP-Brand-slide.jpg;"

        Converted to full CDN URLs. Filters out brand slide images.
        """
        img_field = variant.get("Img", "")
        if not img_field:
            return []

        images = []
        for filename in img_field.split(";"):
            filename = filename.strip()
            if not filename:
                continue
            # Skip generic brand slide images
            if "brand-slide" in filename.lower() or "pdp-brand" in filename.lower():
                continue
            # Build full CDN URL
            full_url = IMAGE_CDN + filename
            # Prefer .webp for smaller files
            if full_url.endswith(".jpg"):
                full_url = full_url.replace(".jpg", ".webp")
            images.append(full_url)

        return images

    def _extract_age_groups(self, variant: dict) -> list[str]:
        """Extract age groups from hashAgeG field.

        hashAgeG format: ["0#0-3 Months", "1#3-6 Months", "2#6-9 Months", ...]
        Returns: ["0-3 Months", "3-6 Months", "6-9 Months", ...]
        """
        raw = variant.get("hashAgeG", [])
        if not isinstance(raw, list):
            return []

        age_groups = []
        for entry in raw:
            if not isinstance(entry, str) or "#" not in entry:
                continue
            # Split on first # — format is "index#label"
            _, _, label = entry.partition("#")
            label = label.strip()
            if label:
                age_groups.append(label)

        return age_groups

    def _extract_colors(self, variant: dict) -> list[str]:
        """Extract color options from hashCols field.

        hashCols format: ["10#Multi Color", "20#Blue"]
        Returns: ["Multi Color", "Blue"]
        """
        raw = variant.get("hashCols", [])
        if not isinstance(raw, list):
            return []

        colors = []
        for entry in raw:
            if not isinstance(entry, str) or "#" not in entry:
                continue
            _, _, label = entry.partition("#")
            label = label.strip()
            if label:
                colors.append(label)

        return colors

    def _extract_brand_from_url(self, url: str) -> str | None:
        """Extract brand name from product URL.

        URL pattern: //www.firstcry.com/{brand}/{slug}/{PID}/product-detail
        Brand is the first path segment after the domain.
        """
        try:
            path = url.split("firstcry.com/")[1]
            brand_slug = path.split("/")[0]
            if brand_slug and brand_slug != "product-detail":
                # Convert slug to title case
                return brand_slug.replace("-", " ").title()
        except (IndexError, AttributeError):
            pass
        return None

    def _build_breadcrumbs(
        self,
        cat_url: str | None,
        scat_url: str | None,
    ) -> list[str]:
        """Build breadcrumb trail from cat_url and scat_url JS variables.

        cat_url: "//www.firstcry.com/toys-and-gaming"
        scat_url: "//www.firstcry.com/play-gyms-and-playmats/5/49"
        """
        crumbs = []

        if cat_url:
            # Extract category name from URL path
            path = cat_url.rstrip("/").split("/")[-1]
            if path and path not in ("www.firstcry.com", "firstcry.com"):
                crumbs.append(path.replace("-", " ").title())

        if scat_url:
            # Extract subcategory — path before the numeric IDs
            parts = scat_url.rstrip("/").split("/")
            # Find the first non-numeric, non-domain segment from the end
            for part in parts:
                if part and not part.isdigit() and "firstcry.com" not in part:
                    name = part.replace("-", " ").title()
                    if name not in crumbs:
                        crumbs.append(name)
                    break

        return crumbs

    def _infer_category(self, breadcrumbs: list[str]) -> str | None:
        """Infer Whydud category slug from breadcrumbs."""
        text = " ".join(breadcrumbs).lower()

        category_keywords = {
            "diaper": "baby-care",
            "wipe": "baby-care",
            "lotion": "baby-care",
            "bath": "baby-care",
            "feeding": "baby-feeding",
            "bottle": "baby-feeding",
            "breast pump": "baby-feeding",
            "food": "baby-feeding",
            "toy": "toys",
            "game": "toys",
            "puzzle": "toys",
            "clothing": "kids-clothing",
            "clothes": "kids-clothing",
            "fashion": "kids-clothing",
            "shoe": "kids-footwear",
            "footwear": "kids-footwear",
            "stroller": "baby-gear",
            "car seat": "baby-gear",
            "carrier": "baby-gear",
            "gear": "baby-gear",
            "nursery": "nursery",
            "crib": "nursery",
            "bedding": "nursery",
            "school": "school-supplies",
            "bag": "school-supplies",
        }

        for keyword, slug in category_keywords.items():
            if keyword in text:
                return slug
        return "baby-care"  # Default for FirstCry products

    # ------------------------------------------------------------------
    # Price helpers
    # ------------------------------------------------------------------

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value (rupees) to Decimal in paisa (* 100)."""
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

    # ------------------------------------------------------------------
    # Block detection
    # ------------------------------------------------------------------

    def _is_blocked(self, response) -> bool:
        """Detect if the site served a block or challenge page."""
        if response.status in (403, 429):
            return True
        if len(response.text) < 500 and "Access Denied" in response.text:
            return True
        return False
