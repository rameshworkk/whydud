"""TataCLiQ spider — scrapes multi-category marketplace listings and details.

Architecture:
  TataCLiQ is a Next.js SSR application.
  - Data source: __NEXT_DATA__ (script#__NEXT_DATA__ type=application/json)
  - JSON-LD Product schema on detail pages as fallback
  - Moderate anti-bot (Cloudflare) — Playwright recommended for reliability
  - Marketplace API: /marketplacewebservices/v2/... endpoints

URL patterns:
  Category: /{category-path}/c-{msh+code}?page={n}&size=40
  Product:  /{product-slug}/p-{mp+code}
  Search:   /search/?searchCategory=all&text={query}&page={n}
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

MARKETPLACE_SLUG = "tata-cliq"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Electronics
    "electronics": "electronics",
    "mobiles": "smartphones",
    "smartphones": "smartphones",
    "mobile-phones": "smartphones",
    "laptops": "laptops",
    "televisions": "televisions",
    "headphones": "audio",
    "speakers": "audio",
    "cameras": "cameras",
    "tablets": "tablets",
    "smartwatches": "smartwatches",
    "smart-watches": "smartwatches",
    # Fashion — Men
    "mens-clothing": "mens-fashion",
    "men-clothing": "mens-fashion",
    "mens-shirts": "mens-fashion",
    "mens-tshirts": "mens-fashion",
    "mens-jeans": "mens-fashion",
    "mens-trousers": "mens-fashion",
    # Fashion — Women
    "womens-clothing": "womens-fashion",
    "women-clothing": "womens-fashion",
    "womens-kurtas": "womens-fashion",
    "womens-dresses": "womens-fashion",
    "womens-tops": "womens-fashion",
    "sarees": "womens-fashion",
    # Footwear
    "footwear": "footwear",
    "mens-footwear": "footwear",
    "womens-footwear": "footwear",
    "sports-shoes": "footwear",
    # Beauty
    "beauty": "beauty",
    "skincare": "skincare",
    "makeup": "makeup",
    "fragrance": "fragrance",
    # Home & Kitchen
    "home-kitchen": "home-decor",
    "home-furnishing": "home-decor",
    "kitchen-appliances": "kitchen-tools",
    # Accessories
    "accessories": "accessories",
    "watches": "watches",
    "jewellery": "jewellery",
    "bags": "accessories",
    "sunglasses": "accessories",
    # Appliances
    "refrigerators": "refrigerators",
    "washing-machines": "washing-machines",
    "air-conditioners": "air-conditioners",
    "air-purifiers": "appliances",
    "vacuum-cleaners": "appliances",
}

# ---------------------------------------------------------------------------
# Seed URLs — TataCLiQ category pages
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Electronics ─────────────────────────────────────────────────────
    ("https://www.tatacliq.com/mobiles/c-msh1210", _TOP),
    ("https://www.tatacliq.com/laptops/c-msh1220", _TOP),
    ("https://www.tatacliq.com/televisions/c-msh1211", _STD),
    ("https://www.tatacliq.com/headphones/c-msh1215", _STD),
    ("https://www.tatacliq.com/cameras/c-msh1214", _STD),
    ("https://www.tatacliq.com/tablets/c-msh1221", _STD),
    ("https://www.tatacliq.com/smart-watches/c-msh1216", _STD),
    # ── Fashion — Men ───────────────────────────────────────────────────
    ("https://www.tatacliq.com/mens-clothing/c-msh1012", _TOP),
    ("https://www.tatacliq.com/mens-footwear/c-msh1013", _STD),
    # ── Fashion — Women ─────────────────────────────────────────────────
    ("https://www.tatacliq.com/womens-clothing/c-msh1011", _TOP),
    ("https://www.tatacliq.com/womens-footwear/c-msh1017", _STD),
    # ── Beauty ──────────────────────────────────────────────────────────
    ("https://www.tatacliq.com/beauty/c-msh13", _STD),
    # ── Home & Kitchen ──────────────────────────────────────────────────
    ("https://www.tatacliq.com/home-kitchen/c-msh14", _STD),
    # ── Watches & Accessories ───────────────────────────────────────────
    ("https://www.tatacliq.com/watches/c-msh1015", _STD),
    ("https://www.tatacliq.com/jewellery/c-msh1016", _STD),
    ("https://www.tatacliq.com/accessories/c-msh1014", _STD),
]

MAX_LISTING_PAGES = 5
PAGE_SIZE = 40


class TataCliqSpider(BaseWhydudSpider):
    """Scrapes TataCLiQ.com multi-category marketplace.

    TataCLiQ uses Next.js with SSR. Product data is in:
    - __NEXT_DATA__ JSON on pages (primary)
    - JSON-LD Product schema on detail pages (fallback)
    - Marketplace API at /marketplacewebservices/v2/ (alternative)

    Cloudflare WAF — Playwright recommended for reliability.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "tata_cliq"
    allowed_domains = ["tatacliq.com", "www.tatacliq.com"]

    QUICK_MODE_CATEGORIES = 5

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 3,
        "CONCURRENT_REQUESTS": 4,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
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
            f"TataCLiQ spider finished ({reason}): "
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
    # start_requests — Playwright for Cloudflare bypass
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

    def _extract_next_data(self, response) -> dict | None:
        """Extract __NEXT_DATA__ JSON from page source."""
        script = response.css('script#__NEXT_DATA__::text').get()
        if not script:
            # Fallback: regex search
            match = re.search(
                r'<script\s+id="__NEXT_DATA__"\s+type="application/json">\s*(\{.+?\})\s*</script>',
                response.text,
                re.DOTALL,
            )
            if match:
                script = match.group(1)
        if not script:
            return None
        try:
            return json.loads(script)
        except (json.JSONDecodeError, ValueError):
            self.logger.warning(f"Failed to parse __NEXT_DATA__ on {response.url}")
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
        """Detect Cloudflare challenge or block page."""
        if response.status in (403, 429, 503):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "just a moment" in title or "attention required" in title:
            return True
        if "access denied" in title or "blocked" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract products from category/search listing page."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Strategy 1: Extract from __NEXT_DATA__
        next_data = self._extract_next_data(response)
        products = []
        if next_data:
            page_props = next_data.get("props", {}).get("pageProps") or {}
            # Try various paths
            for key in ("searchResult", "categoryData", "plpData", "data"):
                section = page_props.get(key) or {}
                prod_list = (
                    section.get("products")
                    or section.get("results")
                    or section.get("items")
                    or section.get("productList")
                    or []
                )
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(f"Found {len(products)} products (__NEXT_DATA__) on {response.url}")
            for prod in products:
                prod_id = prod.get("productId") or prod.get("productCode") or prod.get("id")
                slug = prod.get("url") or prod.get("slug") or ""
                if not prod_id:
                    continue

                if slug and slug.startswith("/"):
                    product_url = f"https://www.tatacliq.com{slug}"
                elif slug:
                    product_url = f"https://www.tatacliq.com/{slug}"
                else:
                    product_url = f"https://www.tatacliq.com/p-{prod_id}"

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
            links = response.css("a[href*='/p-']::attr(href)").getall()
            seen = set()
            for href in links:
                full_url = response.urljoin(href)
                if full_url not in seen and "/p-" in full_url:
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

        # Pagination (0-indexed)
        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 0)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category - 1:
            next_page = pages_so_far + 1
            separator = "&" if "?" in base_url else "?"
            next_url = f"{base_url}{separator}page={next_page}&size={PAGE_SIZE}"
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

        # Extract product code from URL
        code_match = PRODUCT_CODE_RE.search(response.url)
        external_id = code_match.group(1) if code_match else None

        # Strategy 1: __NEXT_DATA__
        next_data = self._extract_next_data(response)
        if next_data:
            page_props = next_data.get("props", {}).get("pageProps") or {}
            product = page_props.get("productData") or page_props.get("product") or page_props.get("data") or {}
            if product and (product.get("productname") or product.get("name")):
                item = self._parse_from_next_data(product, response.url, category_slug, external_id)
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

        # Strategy 3: Build from listing data
        if listing_data:
            item = self._parse_from_listing_data(listing_data, response.url, category_slug, external_id)
            if item:
                self._product_pages_scraped += 1
                self._products_extracted += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # Extraction: __NEXT_DATA__ (primary)
    # ------------------------------------------------------------------

    def _parse_from_next_data(
        self, product: dict, url: str, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Extract product data from __NEXT_DATA__ product object."""
        name = product.get("productname") or product.get("name")
        if not name:
            return None

        pid = external_id or str(product.get("productId") or product.get("productCode") or "")
        if not pid:
            return None

        # Prices
        selling_price = self._parse_price(product.get("price") or product.get("winningSellerPrice"))
        mrp = self._parse_price(product.get("mrp") or product.get("wasPriceData"))

        # Brand
        brand = product.get("brandname") or product.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        # Images
        images = []
        for key in ("imageURL", "image", "productImage"):
            img = product.get(key)
            if img:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, list):
                    images.extend([i for i in img if isinstance(i, str)])
        gallery = product.get("galleryImages") or product.get("images") or []
        for img in gallery:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                images.append(img.get("url") or img.get("imageURL", ""))

        # Rating
        rating = None
        review_count = None
        rating_val = product.get("averageRating") or product.get("rating")
        if rating_val and str(rating_val) not in ("0", "0.0"):
            try:
                rating = Decimal(str(rating_val))
            except (InvalidOperation, ValueError):
                pass
        count_val = product.get("totalRatings") or product.get("reviewCount") or product.get("ratingCount")
        if count_val and str(count_val) != "0":
            try:
                review_count = int(count_val)
            except (ValueError, TypeError):
                pass

        # Stock
        in_stock = product.get("inStock", True)

        # Seller
        seller_name = product.get("sellerName") or product.get("winningSellerName") or "TataCLiQ"

        # Category
        if not category_slug:
            hierarchy = product.get("categoryHierarchy") or []
            for cat in hierarchy:
                cat_lower = cat.lower() if isinstance(cat, str) else ""
                for kw, slug in KEYWORD_CATEGORY_MAP.items():
                    if kw in cat_lower:
                        category_slug = slug
                        break
                if category_slug:
                    break

        # Description
        description = product.get("description") or product.get("productDescription")

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=name,
            brand=brand if brand else None,
            price=selling_price,
            mrp=mrp,
            images=[img for img in images if img],
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
                rating=None,
                review_count=None,
                specs={},
                seller_name=offers.get("seller", {}).get("name", "TataCLiQ") if isinstance(offers.get("seller"), dict) else "TataCLiQ",
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
    # Extraction: Listing data fallback
    # ------------------------------------------------------------------

    def _parse_from_listing_data(
        self, listing: dict, url: str, category_slug: str | None, external_id: str | None,
    ) -> ProductItem | None:
        """Build ProductItem from listing data when detail extraction fails."""
        name = listing.get("productname") or listing.get("name")
        if not name:
            return None

        pid = external_id or str(listing.get("productId") or listing.get("productCode") or "")
        if not pid:
            return None

        selling_price = self._parse_price(listing.get("price"))
        mrp = self._parse_price(listing.get("mrp"))
        brand = listing.get("brandname") or listing.get("brand")

        images = []
        img = listing.get("imageURL") or listing.get("image")
        if img:
            images = [img] if isinstance(img, str) else img

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
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
            manufacturer=brand,
            model_number=None,
            weight=None,
            dimensions=None,
        )
