"""Snapdeal spider — scrapes product listings and detail pages.

Architecture:
  Snapdeal is a traditional server-rendered site (no React/Vue SPA).
  - Listing pages: HTML product cards with .product-tuple-listing divs
  - Detail pages: Hidden inputs + JavaScript variables (sdLogData, pdpConfigs)
  - No Product JSON-LD on detail pages — only BreadcrumbList
  - Pagination via JS-driven "Show next" — use Playwright for pagination

URL patterns:
  Category: /products/{category-slug}
  Product:  /product/{product-name-slug}/{pogId}
  Search:   /search?keyword={term}&sort=rlvncy
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

POG_ID_RE = re.compile(r"/product/[^/]+/(\d+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "snapdeal"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Mobiles
    "mobiles": "smartphones",
    "smartphones": "smartphones",
    "mobile-phones": "smartphones",
    "mobiles-cases-covers": "smartphones",
    "mobile-accessories": "smartphones",
    "power-banks": "smartphones",
    "tablets": "tablets",
    # Electronics
    "electronics-headphones": "audio",
    "headphones": "audio",
    "earphones": "audio",
    "bluetooth-speakers": "audio",
    "speakers": "audio",
    "electronic-headphones-earphones": "audio",
    # Laptops & Computers
    "laptops": "laptops",
    "laptop-accessories": "laptops",
    "pen-drives": "laptops",
    "hard-drives": "laptops",
    "monitors": "laptops",
    "printers": "laptops",
    # Cameras
    "cameras": "cameras",
    "camera-accessories": "cameras",
    # TVs & Entertainment
    "televisions": "televisions",
    "led-tv": "televisions",
    "projectors": "televisions",
    # Large Appliances
    "refrigerators": "refrigerators",
    "washing-machines": "washing-machines",
    "air-conditioners": "air-conditioners",
    "microwave-ovens": "appliances",
    "dishwashers": "appliances",
    "water-heaters": "appliances",
    # Small Appliances
    "air-purifiers": "appliances",
    "vacuum-cleaners": "appliances",
    "fans": "appliances",
    "irons": "appliances",
    "home-appliances": "appliances",
    # Kitchen
    "mixer-grinders": "kitchen-tools",
    "food-processors": "kitchen-tools",
    "electric-kettles": "kitchen-tools",
    "induction-cooktops": "kitchen-tools",
    "gas-stoves": "kitchen-tools",
    "kitchen-appliances": "kitchen-tools",
    # Personal Care
    "trimmers": "grooming",
    "shavers": "grooming",
    "hair-dryers": "grooming",
    "personal-care": "grooming",
    # Fashion (multi-category)
    "men-apparel": "mens-fashion",
    "men-tshirts": "mens-fashion",
    "men-shirts": "mens-fashion",
    "men-jeans": "mens-fashion",
    "women-apparel": "womens-fashion",
    "women-tops": "womens-fashion",
    "women-dresses": "womens-fashion",
    "women-sarees": "womens-fashion",
    "kids-clothing": "kids-fashion",
    # Footwear
    "men-footwear": "footwear",
    "women-footwear": "footwear",
    "men-sports-shoes": "footwear",
    "women-flats": "footwear",
    # Home & Kitchen
    "home-furnishing": "home-decor",
    "home-decoratives": "home-decor",
    "bed-linen": "home-decor",
    # Health & Beauty
    "beauty-products": "beauty",
    "skin-care": "beauty",
    "health-wellness": "wellness",
    # Gaming
    "gaming": "gaming",
}

# ---------------------------------------------------------------------------
# Seed URLs — Snapdeal category pages
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Electronics ─────────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/mobiles", _TOP),
    ("https://www.snapdeal.com/products/electronics-headphones", _TOP),
    ("https://www.snapdeal.com/products/laptops", _STD),
    ("https://www.snapdeal.com/products/tablets", _STD),
    ("https://www.snapdeal.com/products/cameras", _STD),
    ("https://www.snapdeal.com/products/televisions", _STD),
    # ── Home Appliances ─────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/home-appliances", _STD),
    ("https://www.snapdeal.com/products/kitchen-appliances", _STD),
    # ── Fashion — Men ───────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/men-apparel", _TOP),
    ("https://www.snapdeal.com/products/men-footwear", _STD),
    # ── Fashion — Women ─────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/women-apparel", _TOP),
    ("https://www.snapdeal.com/products/women-footwear", _STD),
    # ── Kids ────────────────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/kids-clothing", _STD),
    # ── Home & Kitchen ──────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/home-furnishing", _STD),
    ("https://www.snapdeal.com/products/home-decoratives", _STD),
    # ── Personal Care & Beauty ──────────────────────────────────────────
    ("https://www.snapdeal.com/products/beauty-products", _STD),
    ("https://www.snapdeal.com/products/personal-care", _STD),
    # ── Health ──────────────────────────────────────────────────────────
    ("https://www.snapdeal.com/products/health-wellness", _STD),
]

MAX_LISTING_PAGES = 5


class SnapdealSpider(BaseWhydudSpider):
    """Scrapes Snapdeal.com multi-category marketplace.

    Snapdeal is server-rendered HTML (no SPA framework).
    - Listing pages: .product-tuple-listing divs with product cards
    - Product detail pages: hidden input fields + JavaScript variables

    Key data sources on product pages:
      - Hidden inputs: #productPrice, #brandName, #avgRating, #soldOut, etc.
      - JS variable: sdLogData (price, rating, seller info)
      - OG meta tags: og:price:amount, og:image
      - Image CDN: https://g.sdlcdn.com/imgs/

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "snapdeal"
    allowed_domains = ["snapdeal.com", "www.snapdeal.com"]

    QUICK_MODE_CATEGORIES = 6

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
            f"Snapdeal spider finished ({reason}): "
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
        """Emit HTTP requests for category listing pages."""
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("?")[0].split("/filters/")[0]
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
        path = url.split("?")[0].lower()
        slug_part = path.split("/products/")[-1] if "/products/" in path else ""
        if slug_part in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[slug_part]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
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
        """Detect if Snapdeal served a block/error page."""
        if response.status in (403, 429):
            return True
        if response.status == 404:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        body_text = response.text[:2000].lower()
        if "captcha" in body_text and "challenge" in body_text:
            return True
        return False

    def _extract_js_var(self, response, var_name: str) -> dict | None:
        """Extract a JavaScript variable from page source."""
        # Match: var varName = {...}; or varName = {...};
        pattern = rf"(?:var\s+)?{re.escape(var_name)}\s*=\s*(\{{.+?\}})\s*;?"
        match = re.search(pattern, response.text, re.DOTALL)
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            return None

    def _get_hidden_input(self, response, input_id: str) -> str | None:
        """Get value from a hidden input field by ID."""
        val = response.css(f"input#{input_id}::attr(value)").get()
        if val and val.strip() and val.strip().lower() not in ("null", "undefined", ""):
            return val.strip()
        return None

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from category/search listing page."""
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

        # Extract product cards
        product_links = set()
        cards = response.css(".product-tuple-listing")
        for card in cards:
            href = card.css("a::attr(href)").get()
            if href and "/product/" in href:
                product_links.add(response.urljoin(href))

        # Fallback: any link with /product/ pattern
        if not product_links:
            for href in response.css("a[href*='/product/']::attr(href)").getall():
                full_url = response.urljoin(href)
                if "/product/" in full_url:
                    product_links.add(full_url)

        if product_links:
            self.logger.info(f"Found {len(product_links)} products on {response.url}")
            for prod_url in product_links:
                yield scrapy.Request(
                    prod_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={"category_slug": category_slug},
                )
        else:
            # Try Playwright if HTTP returned no products
            if not response.meta.get("playwright"):
                self.logger.info(f"No products via HTTP on {response.url} — trying Playwright")
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

        # Pagination — Snapdeal uses JS pagination, use Playwright for page 2+
        base_url = response.url.split("?")[0].split("/filters/")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            separator = "&" if "?" in response.url else "?"
            next_url = f"{response.url.split('&page=')[0]}{separator}page={next_page}"
            self._pages_followed[base_url] = next_page

            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page.

        Strategy:
        1. Hidden inputs + sdLogData JS variable (primary)
        2. HTML CSS selectors (fallback)
        3. OG meta tags (last resort)
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

        # Extract pogId from URL
        pog_match = POG_ID_RE.search(response.url)
        pog_id = pog_match.group(1) if pog_match else None

        # Strategy 1: Hidden inputs + JS variables
        item = self._parse_from_hidden_inputs(response, category_slug, pog_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 2: HTML extraction
        item = self._parse_from_html(response, category_slug, pog_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: OG meta tags
        item = self._parse_from_og_meta(response, category_slug, pog_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Playwright fallback
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
    # Extraction: Hidden inputs + JS variables (primary)
    # ------------------------------------------------------------------

    def _parse_from_hidden_inputs(
        self, response, category_slug: str | None, pog_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from hidden inputs and sdLogData."""
        # Product name from hidden input or h1
        title = self._get_hidden_input(response, "productNamePDP")
        if not title:
            title = response.css("h1::text").get()
        if not title:
            return None
        title = title.strip()

        # External ID
        external_id = self._get_hidden_input(response, "pogId") or pog_id
        if not external_id:
            return None

        # Price from hidden input
        price_val = self._get_hidden_input(response, "productPrice")
        price = self._parse_price(price_val)

        # Brand
        brand = self._get_hidden_input(response, "brandName")

        # Rating
        rating = None
        review_count = None
        avg_rating_str = self._get_hidden_input(response, "avgRating")
        if avg_rating_str:
            try:
                rating = Decimal(avg_rating_str)
                if rating == 0:
                    rating = None
            except (InvalidOperation, ValueError):
                pass

        # Try sdLogData for additional info
        sd_log = self._extract_js_var(response, "sdLogData")
        if sd_log:
            if not price:
                price = self._parse_price(str(sd_log.get("price", "")))
            if not rating and sd_log.get("rating"):
                try:
                    rating = Decimal(str(sd_log["rating"]))
                    if rating == 0:
                        rating = None
                except (InvalidOperation, ValueError):
                    pass
            if sd_log.get("ratingCt"):
                try:
                    review_count = int(sd_log["ratingCt"])
                    if review_count == 0:
                        review_count = None
                except (ValueError, TypeError):
                    pass

        # MRP from HTML
        mrp_text = response.css(".discount-price.strike::text").get()
        mrp = self._parse_price(mrp_text)

        # Stock
        sold_out = self._get_hidden_input(response, "soldOut")
        in_stock = sold_out != "true"

        # Images
        images = []
        for img in response.css("img[data-src]::attr(data-src), img.lazy-load::attr(data-src)").getall():
            if img and "sdlcdn.com" in img:
                # Get full-size image by removing resize params
                clean = img.split("?")[0]
                images.append(clean)
        if not images:
            for img in response.css(".thumbnail-list img::attr(src), .pdp-image img::attr(src)").getall():
                if img and not img.startswith("data:"):
                    images.append(img.split("?")[0])

        # Specs
        specs = {}
        for row in response.css(".specification-row, .detailssubbox tr"):
            label = row.css(".spec-label::text, td:first-child::text").get()
            value = row.css(".spec-value::text, td:last-child::text").get()
            if label and value:
                specs[label.strip()] = value.strip()

        # Seller
        seller_name = response.css(".seller-details a::text").get()
        seller_rating = None
        if sd_log and sd_log.get("sellerRating"):
            try:
                seller_rating = Decimal(str(sd_log["sellerRating"]))
            except (InvalidOperation, ValueError):
                pass

        # Breadcrumbs
        breadcrumbs = [
            bc.strip()
            for bc in response.css(".bCrumbOmniTrack a::text, .bCrumbOmniTrack span::text").getall()
            if bc.strip()
        ]

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=response.url,
            title=title,
            brand=brand,
            price=price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name=seller_name.strip() if seller_name else "Snapdeal",
            seller_rating=seller_rating,
            in_stock=in_stock,
            fulfilled_by="Snapdeal",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=None,
            warranty=specs.get("Warranty") or specs.get("warranty"),
            delivery_info=None,
            return_policy=None,
            breadcrumbs=breadcrumbs,
            variant_options=[],
            country_of_origin=specs.get("Country of Origin"),
            manufacturer=specs.get("Manufacturer") or brand,
            model_number=specs.get("Model Number") or specs.get("Model Name"),
            weight=specs.get("Weight") or specs.get("Product Weight"),
            dimensions=specs.get("Dimensions"),
        )

    # ------------------------------------------------------------------
    # Extraction: HTML CSS selectors (fallback)
    # ------------------------------------------------------------------

    def _parse_from_html(
        self, response, category_slug: str | None, pog_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from HTML as fallback."""
        title = response.css("h1::text, .pdp-e-i-head::text").get()
        if not title:
            return None
        title = title.strip()

        external_id = pog_id
        if not external_id:
            return None

        price_text = response.css(
            ".payBlkBig::text, .pdp-final-price span::text, .mrp::text"
        ).get()
        price = self._parse_price(price_text)

        mrp_text = response.css(".discount-price.strike::text, .original-price::text").get()
        mrp = self._parse_price(mrp_text)

        brand = response.css("a[href*='/brand/']::text, .pdp-e-i-head .head-brand a::text").get()

        images = response.css(
            ".pdp-image img::attr(src), .pdpImage img::attr(src)"
        ).getall()
        images = [img.split("?")[0] for img in images if img and not img.startswith("data:")]

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=response.url,
            title=title,
            brand=brand.strip() if brand else None,
            price=price,
            mrp=mrp,
            images=images,
            rating=None,
            review_count=None,
            specs={},
            seller_name="Snapdeal",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Snapdeal",
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
    # Extraction: OG meta tags (last resort)
    # ------------------------------------------------------------------

    def _parse_from_og_meta(
        self, response, category_slug: str | None, pog_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from OpenGraph meta tags."""
        title = response.css("meta[property='og:title']::attr(content)").get()
        if not title:
            return None

        external_id = pog_id
        if not external_id:
            return None

        price_str = response.css("meta[property='og:price:amount']::attr(content)").get()
        price = self._parse_price(price_str)

        image = response.css("meta[property='og:image']::attr(content)").get()
        images = [image] if image else []

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=external_id,
            url=response.url,
            title=title,
            brand=None,
            price=price,
            mrp=None,
            images=images,
            rating=None,
            review_count=None,
            specs={},
            seller_name="Snapdeal",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Snapdeal",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=response.css("meta[property='og:description']::attr(content)").get(),
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
