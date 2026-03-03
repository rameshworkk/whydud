"""Nykaa spider — scrapes beauty & personal care product listings and details.

Architecture:
  Nykaa is a custom React SPA (NOT Next.js) with Redux state management.
  - Data source: window.__PRELOADED_STATE__ (Redux store)
  - JSON-LD Product schema on detail pages as fallback
  - Akamai Bot Manager requires Playwright for ALL pages (403 on plain HTTP)
  - Gateway API: /gateway-api/... endpoints return JSON directly

URL patterns:
  Category: /{category-name}/c/{numeric-id}?page_no={n}
  Product:  /{product-slug}/p/{product-id}
  Search:   /search/result/?q={query}&page_no={n}
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

PRODUCT_ID_RE = re.compile(r"/p/(\d+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "nykaa"

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
    "serum": "skincare",
    "serums": "skincare",
    "face-masks": "skincare",
    "toner": "skincare",
    "eye-cream": "skincare",
    "lip-care": "skincare",
    "anti-aging": "skincare",
    "acne": "skincare",
    # Makeup
    "makeup": "makeup",
    "foundation": "makeup",
    "concealer": "makeup",
    "lipstick": "makeup",
    "lip-color": "makeup",
    "lip gloss": "makeup",
    "mascara": "makeup",
    "eyeliner": "makeup",
    "eyeshadow": "makeup",
    "blush": "makeup",
    "compact": "makeup",
    "kajal": "makeup",
    "primer": "makeup",
    "nail-polish": "makeup",
    "nail polish": "makeup",
    "setting-spray": "makeup",
    # Hair Care
    "hair": "hair-care",
    "shampoo": "hair-care",
    "conditioner": "hair-care",
    "hair-oil": "hair-care",
    "hair oil": "hair-care",
    "hair-serum": "hair-care",
    "hair serum": "hair-care",
    "hair-mask": "hair-care",
    "hair-color": "hair-care",
    "hair color": "hair-care",
    # Bath & Body
    "bath-and-body": "bath-body",
    "bath-body": "bath-body",
    "body-lotion": "bath-body",
    "body lotion": "bath-body",
    "shower-gel": "bath-body",
    "body-wash": "bath-body",
    "deodorant": "bath-body",
    "perfume": "fragrance",
    "fragrance": "fragrance",
    # Men's Grooming
    "men": "grooming",
    "mens-grooming": "grooming",
    "beard": "grooming",
    "shaving": "grooming",
    "after-shave": "grooming",
    # Natural & Wellness
    "natural": "wellness",
    "wellness": "wellness",
    "health-and-wellness": "wellness",
    "supplements": "wellness",
    "vitamins": "wellness",
    # Mom & Baby
    "mom-and-baby": "baby-care",
    "baby": "baby-care",
    # Appliances
    "appliances": "beauty-appliances",
    "hair-dryer": "beauty-appliances",
    "straightener": "beauty-appliances",
    "trimmer": "beauty-appliances",
    # Luxe
    "luxe": "luxury-beauty",
}

# ---------------------------------------------------------------------------
# Seed URLs — Nykaa category pages
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Skincare ────────────────────────────────────────────────────────
    ("https://www.nykaa.com/skin/c/5116", _TOP),
    ("https://www.nykaa.com/skin/moisturizers/c/6627", _STD),
    ("https://www.nykaa.com/skin/sunscreen/c/6709", _STD),
    ("https://www.nykaa.com/skin/face-wash-and-cleanser/c/6628", _STD),
    ("https://www.nykaa.com/skin/face-serum/c/6632", _STD),
    # ── Makeup ──────────────────────────────────────────────────────────
    ("https://www.nykaa.com/makeup/c/5117", _TOP),
    ("https://www.nykaa.com/makeup/lips/lipstick/c/5640", _STD),
    ("https://www.nykaa.com/makeup/face/foundation/c/5166", _STD),
    ("https://www.nykaa.com/makeup/eyes/mascara/c/5714", _STD),
    ("https://www.nykaa.com/makeup/eyes/eyeliner/c/5692", _STD),
    # ── Hair Care ───────────────────────────────────────────────────────
    ("https://www.nykaa.com/hair/c/5118", _TOP),
    ("https://www.nykaa.com/hair/shampoo/c/6634", _STD),
    ("https://www.nykaa.com/hair/conditioner/c/6635", _STD),
    ("https://www.nykaa.com/hair/hair-oil/c/6636", _STD),
    # ── Bath & Body ─────────────────────────────────────────────────────
    ("https://www.nykaa.com/bath-and-body/c/5121", _TOP),
    ("https://www.nykaa.com/bath-and-body/body-lotion/c/6644", _STD),
    ("https://www.nykaa.com/bath-and-body/shower-gel/c/6643", _STD),
    # ── Fragrance ───────────────────────────────────────────────────────
    ("https://www.nykaa.com/fragrance/c/5166", _STD),
    # ── Men ─────────────────────────────────────────────────────────────
    ("https://www.nykaa.com/men/c/5179", _TOP),
    # ── Natural ─────────────────────────────────────────────────────────
    ("https://www.nykaa.com/natural/c/5392", _STD),
    # ── Health & Wellness ───────────────────────────────────────────────
    ("https://www.nykaa.com/health-and-wellness/c/5124", _STD),
    # ── Mom & Baby ──────────────────────────────────────────────────────
    ("https://www.nykaa.com/mom-and-baby/c/5123", _STD),
    # ── Luxe ────────────────────────────────────────────────────────────
    ("https://www.nykaa.com/luxe/c/8766", _STD),
    # ── Appliances ──────────────────────────────────────────────────────
    ("https://www.nykaa.com/appliances/c/5119", _STD),
]

MAX_LISTING_PAGES = 5


class NykaaSpider(BaseWhydudSpider):
    """Scrapes Nykaa.com beauty & personal care marketplace.

    Nykaa uses Akamai Bot Manager — requires Playwright for ALL pages.
    Product data is in window.__PRELOADED_STATE__ (Redux store).
    JSON-LD Product schema available on detail pages as fallback.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "nykaa"
    allowed_domains = ["nykaa.com", "www.nykaa.com"]

    QUICK_MODE_CATEGORIES = 5

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS": 6,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 3,
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
            f"Nykaa spider finished ({reason}): "
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
    # start_requests — Playwright required (Akamai Bot Manager)
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit Playwright requests for category listing pages."""
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("?")[0]
            self._max_pages_map[base] = max_pg

            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": self._resolve_category_from_url(url),
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", random.randint(3000, 5000)),
                    ],
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (Playwright)")

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
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None

    def _extract_preloaded_state(self, response) -> dict | None:
        """Extract window.__PRELOADED_STATE__ JSON from page source."""
        match = re.search(
            r"window\.__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;?\s*</script>",
            response.text,
            re.DOTALL,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"Failed to parse __PRELOADED_STATE__ on {response.url}")
            return None

    def _parse_price(self, price_val) -> Decimal | None:
        """Parse price value to Decimal in paisa."""
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
        """Detect if Nykaa served a block/challenge page."""
        if response.status in (403, 429):
            return True
        # Akamai challenge pages are typically small
        if len(response.text) < 500:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages (Playwright only)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from category listing page."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: Extract from __PRELOADED_STATE__
        state = self._extract_preloaded_state(response)
        products = []
        if state:
            # Try various paths in the Redux state
            for key in ("category", "search", "productListing"):
                section = state.get(key) or {}
                prod_list = section.get("products") or section.get("results") or section.get("items") or []
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(f"Found {len(products)} products (state) on {response.url}")
            for prod in products:
                prod_id = prod.get("id") or prod.get("productId") or prod.get("sku")
                slug = prod.get("slug") or prod.get("actionUrl") or ""
                if not prod_id:
                    continue

                if slug and slug.startswith("/"):
                    product_url = f"https://www.nykaa.com{slug}"
                elif slug:
                    product_url = f"https://www.nykaa.com/{slug}"
                else:
                    product_url = f"https://www.nykaa.com/p/{prod_id}"

                yield scrapy.Request(
                    product_url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "category_slug": category_slug,
                        "listing_data": prod,
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "domcontentloaded"),
                            PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                        ],
                    },
                )
        else:
            # Strategy 2: HTML product links
            links = response.css("a[href*='/p/']::attr(href)").getall()
            seen = set()
            for href in links:
                full_url = response.urljoin(href)
                if full_url not in seen and "/p/" in full_url:
                    seen.add(full_url)
                    yield scrapy.Request(
                        full_url,
                        callback=self.parse_product_page,
                        errback=self.handle_error,
                        headers=self._make_headers(),
                        meta={
                            "category_slug": category_slug,
                            "playwright": True,
                            "playwright_page_init_callback": self._apply_stealth,
                            "playwright_page_methods": [
                                PageMethod("wait_for_load_state", "domcontentloaded"),
                                PageMethod("wait_for_timeout", random.randint(2000, 4000)),
                            ],
                        },
                    )
            if not links:
                self.logger.warning(f"No products found on {response.url}")
                return

        # Pagination
        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page_no={next_page}"
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
                        PageMethod("wait_for_timeout", random.randint(3000, 5000)),
                    ],
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
        listing_data = response.meta.get("listing_data")

        # Extract product ID from URL
        id_match = PRODUCT_ID_RE.search(response.url)
        external_id = id_match.group(1) if id_match else None

        # Strategy 1: __PRELOADED_STATE__ → productPage
        state = self._extract_preloaded_state(response)
        if state:
            product = None
            for key in ("productPage", "product", "pdp"):
                section = state.get(key) or {}
                if isinstance(section, dict) and section.get("name"):
                    product = section
                    break
                prod_inner = section.get("product") or section.get("productDetails")
                if isinstance(prod_inner, dict) and prod_inner.get("name"):
                    product = prod_inner
                    break

            if product:
                item = self._parse_from_state(product, response.url, category_slug, external_id)
                if item:
                    self._product_pages_scraped += 1
                    self._products_extracted += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug, external_id)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: Build from listing data + HTML
        if listing_data:
            item = self._parse_from_listing_data(listing_data, response, category_slug, external_id)
            if item:
                self._product_pages_scraped += 1
                self._products_extracted += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # Extraction: __PRELOADED_STATE__ (primary)
    # ------------------------------------------------------------------

    def _parse_from_state(
        self, product: dict, url: str, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from __PRELOADED_STATE__ product object."""
        name = product.get("name") or product.get("title")
        if not name:
            return None

        pid = external_id or str(product.get("id") or product.get("productId") or "")
        if not pid:
            return None

        # Prices
        selling_price = self._parse_price(product.get("price") or product.get("offerPrice"))
        mrp = self._parse_price(product.get("mrp") or product.get("originalPrice"))

        # Brand
        brand = product.get("brandName") or product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        # Images
        images = []
        for key in ("imageUrl", "thumbnailUrl", "image"):
            img = product.get(key)
            if img:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, list):
                    images.extend(img)
        img_list = product.get("images") or product.get("imageUrls") or []
        for img in img_list:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                images.append(img.get("url") or img.get("src", ""))

        # Rating
        rating = None
        review_count = None
        rating_val = product.get("rating") or product.get("averageRating")
        if rating_val and str(rating_val) not in ("0", "0.0"):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = product.get("reviewCount") or product.get("totalReviews")
        if count_val and str(count_val) != "0":
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = product.get("inStock", True)

        # Description
        description = product.get("description") or product.get("productDescription")

        # Category
        if not category_slug:
            cat_name = (product.get("categoryName") or product.get("category") or "").lower()
            for kw, slug in KEYWORD_CATEGORY_MAP.items():
                if kw in cat_name:
                    category_slug = slug
                    break

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
            seller_name="Nykaa",
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
    # Extraction: JSON-LD (fallback)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self, response, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from JSON-LD structured data."""
        ld_scripts = response.css('script[type="application/ld+json"]::text').getall()
        for script_text in ld_scripts:
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
            if not name:
                continue

            sku = ld_data.get("sku") or external_id
            if not sku:
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

            rating = None
            review_count = None
            agg_rating = ld_data.get("aggregateRating") or {}
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
            if "OutOfStock" in availability:
                in_stock = False

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url,
                title=name,
                brand=brand,
                price=price,
                mrp=None,
                images=images,
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
        self, listing: dict, response, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Build a ProductItem from listing data when detail page extraction fails."""
        name = listing.get("name") or listing.get("title")
        if not name:
            return None

        pid = external_id or str(listing.get("id") or listing.get("productId") or "")
        if not pid:
            return None

        selling_price = self._parse_price(listing.get("price") or listing.get("offerPrice"))
        mrp = self._parse_price(listing.get("mrp"))

        brand = listing.get("brandName") or listing.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = []
        img = listing.get("imageUrl") or listing.get("thumbnailUrl")
        if img:
            images = [img] if isinstance(img, str) else img

        rating = None
        if listing.get("rating"):
            try:
                rating = Decimal(str(listing["rating"]))
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
            in_stock=True,
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
