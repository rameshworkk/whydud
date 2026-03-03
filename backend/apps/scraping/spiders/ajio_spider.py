"""AJIO spider — scrapes Reliance fashion/lifestyle marketplace.

Architecture:
  AJIO is a React SPA (Reliance-owned), likely PerimeterX anti-bot.
  - Data source: window.__PRELOADED_STATE__ or __NEXT_DATA__
  - JSON-LD on product pages
  - Playwright required for all pages

URL patterns:
  Category: /{category}/c/{category-id}?query=:relevance
  Product:  /{product-slug}/p/{product-id}
  Search:   /search/?text={query}
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

PRODUCT_ID_RE = re.compile(r"/p/(\w+)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "ajio"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Men
    "men-tshirts": "mens-fashion",
    "men-shirts": "mens-fashion",
    "men-jeans": "mens-fashion",
    "men-trousers": "mens-fashion",
    "men-jackets": "mens-fashion",
    "men-kurtas": "mens-fashion",
    "men-clothing": "mens-fashion",
    "men-shorts": "mens-fashion",
    "men-innerwear": "mens-fashion",
    # Women
    "women-kurtas": "womens-fashion",
    "women-tops": "womens-fashion",
    "women-dresses": "womens-fashion",
    "women-jeans": "womens-fashion",
    "women-sarees": "womens-fashion",
    "women-clothing": "womens-fashion",
    "women-ethnic-wear": "womens-fashion",
    "women-western-wear": "womens-fashion",
    # Kids
    "kids-clothing": "kids-fashion",
    "boys-clothing": "kids-fashion",
    "girls-clothing": "kids-fashion",
    # Footwear
    "men-footwear": "footwear",
    "men-casual-shoes": "footwear",
    "men-sports-shoes": "footwear",
    "women-footwear": "footwear",
    "women-flats": "footwear",
    "women-heels": "footwear",
    "sneakers": "footwear",
    # Accessories
    "watches": "watches",
    "sunglasses": "accessories",
    "bags": "accessories",
    "belts": "accessories",
    "wallets": "accessories",
    "jewellery": "jewellery",
    # Home
    "home-decor": "home-decor",
    "home-furnishing": "home-decor",
    # Beauty
    "beauty": "beauty",
    "skincare": "skincare",
    "fragrance": "fragrance",
}

# ---------------------------------------------------------------------------
# Seed URLs
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Men ─────────────────────────────────────────────────────────────
    ("https://www.ajio.com/men-tshirts/c/830216001", _TOP),
    ("https://www.ajio.com/men-shirts/c/830216002", _STD),
    ("https://www.ajio.com/men-jeans/c/830216003", _STD),
    ("https://www.ajio.com/men-trousers/c/830216004", _STD),
    ("https://www.ajio.com/men-jackets-coats/c/830216005", _STD),
    ("https://www.ajio.com/men-kurtas/c/830216010", _STD),
    # ── Women ───────────────────────────────────────────────────────────
    ("https://www.ajio.com/women-kurtas-kurtis/c/830318001", _TOP),
    ("https://www.ajio.com/women-tops-tees/c/830318002", _STD),
    ("https://www.ajio.com/women-dresses/c/830318003", _STD),
    ("https://www.ajio.com/women-sarees/c/830318010", _STD),
    ("https://www.ajio.com/women-jeans/c/830318004", _STD),
    # ── Kids ────────────────────────────────────────────────────────────
    ("https://www.ajio.com/kids-clothing/c/830420001", _STD),
    # ── Footwear ────────────────────────────────────────────────────────
    ("https://www.ajio.com/men-casual-shoes/c/830116002", _TOP),
    ("https://www.ajio.com/men-sports-shoes/c/830116003", _STD),
    ("https://www.ajio.com/women-flats/c/830218002", _STD),
    ("https://www.ajio.com/women-heels/c/830218003", _STD),
    ("https://www.ajio.com/sneakers/c/830116010", _STD),
    # ── Watches & Accessories ───────────────────────────────────────────
    ("https://www.ajio.com/men-watches/c/830516001", _STD),
    ("https://www.ajio.com/women-watches/c/830518001", _STD),
    ("https://www.ajio.com/bags-luggage/c/830600001", _STD),
    ("https://www.ajio.com/sunglasses/c/830700001", _STD),
    # ── Home ────────────────────────────────────────────────────────────
    ("https://www.ajio.com/home-furnishing/c/831000001", _STD),
    # ── Beauty ──────────────────────────────────────────────────────────
    ("https://www.ajio.com/beauty/c/831100001", _STD),
]

MAX_LISTING_PAGES = 5


class AjioSpider(BaseWhydudSpider):
    """Scrapes AJIO.com fashion/lifestyle marketplace.

    AJIO is Reliance-owned, React SPA with PerimeterX anti-bot.
    Playwright required for ALL pages.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "ajio"
    allowed_domains = ["ajio.com", "www.ajio.com"]

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
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"AJIO spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"failed={self.items_failed}"
        )

    async def _apply_stealth(self, page, request):
        try:
            await self.STEALTH.apply_stealth_async(page)
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(45000)
        except Exception as e:
            self.logger.warning(f"Stealth setup issue: {e}")

    def start_requests(self):
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("?")[0]
            self._max_pages_map[base] = max_pg

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
                        PageMethod("wait_for_timeout", random.randint(3000, 6000)),
                    ],
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (Playwright)")

    def _load_urls(self) -> list[tuple[str, int]]:
        fallback = self._max_pages_override or MAX_LISTING_PAGES
        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]
        if self._max_pages_override is not None:
            if self._max_pages_override <= 3:
                return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS[:self.QUICK_MODE_CATEGORIES]]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    def _resolve_category_from_url(self, url: str) -> str | None:
        path = url.split("?")[0].lower()
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in path:
                return slug
        return None

    def _parse_price(self, price_val) -> Decimal | None:
        if price_val is None:
            return None
        try:
            val_str = str(price_val).replace(",", "")
            match = PRICE_RE.search(val_str)
            if not match:
                return None
            rupees = Decimal(match.group().replace(",", ""))
            return rupees * 100 if rupees > 0 else None
        except (InvalidOperation, ValueError):
            return None

    def _is_blocked(self, response) -> bool:
        if response.status in (403, 429):
            return True
        if len(response.text) < 500:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        return "access denied" in title or "blocked" in title or "pardon" in title

    def _extract_state(self, response) -> dict | None:
        """Extract __PRELOADED_STATE__ or __NEXT_DATA__."""
        for pattern in [
            r"window\.__PRELOADED_STATE__\s*=\s*(\{.+?\})\s*;?\s*</script>",
            r'<script\s+id="__NEXT_DATA__"[^>]*>\s*(\{.+?\})\s*</script>',
        ]:
            match = re.search(pattern, response.text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except (json.JSONDecodeError, ValueError):
                    continue
        return None

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url}")
            return

        category_slug = response.meta.get("category_slug")

        # Extract product links
        state = self._extract_state(response)
        products = []
        if state:
            # Try various paths
            page_props = state.get("props", {}).get("pageProps") or state
            for key in ("products", "searchData", "plpData", "results", "category"):
                section = page_props.get(key) or {}
                prod_list = section.get("products") or section.get("results") or section.get("items") or []
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(f"Found {len(products)} products on {response.url}")
            for prod in products:
                slug = prod.get("url") or prod.get("slug") or prod.get("fnlColorVariantData", {}).get("url", "")
                prod_id = prod.get("code") or prod.get("id") or prod.get("productId")
                if not slug and not prod_id:
                    continue

                if slug and slug.startswith("/"):
                    product_url = f"https://www.ajio.com{slug}"
                elif prod_id:
                    product_url = f"https://www.ajio.com/p/{prod_id}"
                else:
                    product_url = f"https://www.ajio.com/{slug}"

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
            links = set()
            for href in response.css("a[href*='/p/']::attr(href)").getall():
                full = response.urljoin(href)
                if "/p/" in full:
                    links.add(full)
            if links:
                self.logger.info(f"Found {len(links)} products (HTML) on {response.url}")
                for prod_url in links:
                    yield scrapy.Request(
                        prod_url,
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
            else:
                self.logger.warning(f"No products found on {response.url}")
                return

        # Pagination
        base_url = response.url.split("?")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)

        if pages_so_far < max_for_category:
            next_page = pages_so_far + 1
            separator = "&" if "?" in response.url else "?"
            base = response.url.split("&page=")[0].split("?page=")[0]
            next_url = f"{base}{separator}page={next_page}"
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
                        PageMethod("wait_for_timeout", random.randint(3000, 6000)),
                    ],
                },
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        if self._is_blocked(response):
            self.logger.warning(f"Blocked on product {response.url}")
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        listing_data = response.meta.get("listing_data")

        id_match = PRODUCT_ID_RE.search(response.url)
        external_id = id_match.group(1) if id_match else None

        # Strategy 1: JS state
        state = self._extract_state(response)
        if state:
            page_props = state.get("props", {}).get("pageProps") or state
            product = page_props.get("productData") or page_props.get("product") or page_props.get("pdpData") or {}
            if product and (product.get("name") or product.get("productName")):
                item = self._build_item(product, response.url, category_slug, external_id)
                if item:
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD
        for script_text in response.css('script[type="application/ld+json"]::text').getall():
            try:
                ld = json.loads(script_text)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(ld, list):
                ld = next((i for i in ld if i.get("@type") == "Product"), None)
                if not ld:
                    continue
            if ld.get("@type") != "Product":
                continue

            name = ld.get("name")
            sku = ld.get("sku") or external_id
            if not name or not sku:
                continue

            offers = ld.get("offers") or {}
            if isinstance(offers, list):
                offers = offers[0] if offers else {}

            brand_data = ld.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else None
            images = ld.get("image") or []
            if isinstance(images, str):
                images = [images]

            item = ProductItem(
                marketplace_slug=MARKETPLACE_SLUG, external_id=str(sku), url=response.url,
                title=name, brand=brand, price=self._parse_price(offers.get("price")),
                mrp=None, images=images, rating=None, review_count=None, specs={},
                seller_name="AJIO", seller_rating=None,
                in_stock="OutOfStock" not in (offers.get("availability") or ""),
                fulfilled_by="AJIO", category_slug=category_slug, about_bullets=[],
                offer_details=[], raw_html_path=None, description=ld.get("description"),
                warranty=None, delivery_info=None, return_policy=None, breadcrumbs=[],
                variant_options=[], country_of_origin=None, manufacturer=brand,
                model_number=None, weight=None, dimensions=None,
            )
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: Listing data
        if listing_data:
            item = self._build_item(listing_data, response.url, category_slug, external_id)
            if item:
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract from {response.url}")
        self.items_failed += 1

    def _build_item(self, data: dict, url: str, category_slug: str | None, external_id: str | None) -> ProductItem | None:
        name = data.get("name") or data.get("productName")
        if not name:
            return None

        pid = external_id or str(data.get("code") or data.get("id") or data.get("productId") or "")
        if not pid:
            return None

        selling_price = self._parse_price(data.get("price") or data.get("offerPrice") or data.get("discountedPrice"))
        mrp = self._parse_price(data.get("mrp") or data.get("wasPriceData") or data.get("originalPrice"))

        brand = data.get("brandName") or data.get("brand")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = []
        for key in ("images", "imageUrls", "galleryImages"):
            img_list = data.get(key) or []
            for img in img_list:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, dict):
                    images.append(img.get("url") or img.get("src", ""))
        if not images:
            img = data.get("imageURL") or data.get("image")
            if img:
                images = [img] if isinstance(img, str) else img

        rating = None
        review_count = None
        if data.get("rating") or data.get("averageRating"):
            try:
                rating = Decimal(str(data.get("rating") or data.get("averageRating")))
            except (InvalidOperation, ValueError):
                pass
        if data.get("reviewCount") or data.get("totalRatings"):
            try:
                review_count = int(data.get("reviewCount") or data.get("totalRatings"))
            except (ValueError, TypeError):
                pass

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pid,
            url=url,
            title=name,
            brand=brand,
            price=selling_price,
            mrp=mrp,
            images=[img for img in images if img],
            rating=rating,
            review_count=review_count,
            specs={},
            seller_name="AJIO",
            seller_rating=None,
            in_stock=data.get("inStock", True),
            fulfilled_by="AJIO",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=data.get("description") or data.get("productDescription"),
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
