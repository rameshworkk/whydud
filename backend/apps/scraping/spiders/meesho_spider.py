"""Meesho spider — scrapes budget marketplace listings and details.

Architecture:
  Meesho is a React SPA with VERY aggressive anti-bot detection.
  - Mandatory Indian residential proxies
  - Multi-layered detection (TLS fingerprinting, behavior analysis)
  - Data source: window.__NEXT_DATA__ or window.__INITIAL_STATE__
  - JSON-LD on product pages
  - Playwright required for ALL pages

URL patterns:
  Category: /pl/{category_code}
  Product:  /p/{product-id}
  Search:   /search?q={query}
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

MARKETPLACE_SLUG = "meesho"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Fashion — Women
    "womens-clothing": "womens-fashion",
    "sarees": "womens-fashion",
    "kurtis": "womens-fashion",
    "kurtas": "womens-fashion",
    "women-tops": "womens-fashion",
    "women-dresses": "womens-fashion",
    "lehengas": "womens-fashion",
    "salwar-suits": "womens-fashion",
    "womens-western-wear": "womens-fashion",
    "women-nightwear": "womens-fashion",
    "dupattas": "womens-fashion",
    # Fashion — Men
    "mens-clothing": "mens-fashion",
    "mens-tshirts": "mens-fashion",
    "mens-shirts": "mens-fashion",
    "mens-jeans": "mens-fashion",
    "mens-track-pants": "mens-fashion",
    "mens-trousers": "mens-fashion",
    "mens-kurtas": "mens-fashion",
    # Kids
    "kids-clothing": "kids-fashion",
    "girls-clothing": "kids-fashion",
    "boys-clothing": "kids-fashion",
    # Footwear
    "mens-footwear": "footwear",
    "womens-footwear": "footwear",
    "sports-shoes": "footwear",
    "sandals": "footwear",
    "slippers": "footwear",
    # Home
    "home-furnishing": "home-decor",
    "bedsheets": "home-decor",
    "curtains": "home-decor",
    "cushion-covers": "home-decor",
    "home-decor": "home-decor",
    # Beauty
    "beauty": "beauty",
    "skincare": "skincare",
    "makeup": "makeup",
    "hair-care": "hair-care",
    # Accessories
    "jewellery": "jewellery",
    "watches": "watches",
    "bags": "accessories",
    "sunglasses": "accessories",
    # Kitchen
    "kitchen": "kitchen-tools",
    "kitchen-tools": "kitchen-tools",
    # Electronics
    "electronics": "electronics",
    "mobile-accessories": "smartphones",
    "headphones": "audio",
    "speakers": "audio",
}

# ---------------------------------------------------------------------------
# Seed URLs
# ---------------------------------------------------------------------------

_TOP = 8
_STD = 4

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Women's Fashion (Meesho's biggest segment) ─────────────────────
    ("https://www.meesho.com/sarees/pl/w0m", _TOP),
    ("https://www.meesho.com/kurtis/pl/w0m", _TOP),
    ("https://www.meesho.com/women-tops/pl/w0m", _STD),
    ("https://www.meesho.com/women-dresses/pl/w0m", _STD),
    ("https://www.meesho.com/salwar-suits/pl/w0m", _STD),
    ("https://www.meesho.com/lehengas/pl/w0m", _STD),
    # ── Men's Fashion ───────────────────────────────────────────────────
    ("https://www.meesho.com/mens-tshirts/pl/w0m", _TOP),
    ("https://www.meesho.com/mens-shirts/pl/w0m", _STD),
    ("https://www.meesho.com/mens-jeans/pl/w0m", _STD),
    # ── Kids ────────────────────────────────────────────────────────────
    ("https://www.meesho.com/kids-clothing/pl/w0m", _STD),
    # ── Footwear ────────────────────────────────────────────────────────
    ("https://www.meesho.com/mens-footwear/pl/w0m", _STD),
    ("https://www.meesho.com/womens-footwear/pl/w0m", _STD),
    # ── Home ────────────────────────────────────────────────────────────
    ("https://www.meesho.com/bedsheets/pl/w0m", _STD),
    ("https://www.meesho.com/home-decor/pl/w0m", _STD),
    # ── Beauty & Accessories ────────────────────────────────────────────
    ("https://www.meesho.com/jewellery/pl/w0m", _STD),
    ("https://www.meesho.com/beauty/pl/w0m", _STD),
    ("https://www.meesho.com/bags/pl/w0m", _STD),
    # ── Electronics ─────────────────────────────────────────────────────
    ("https://www.meesho.com/mobile-accessories/pl/w0m", _STD),
    ("https://www.meesho.com/headphones/pl/w0m", _STD),
]

MAX_LISTING_PAGES = 3  # Lower than others — very aggressive anti-bot


class MeeshoSpider(BaseWhydudSpider):
    """Scrapes Meesho.com budget marketplace.

    Meesho has the MOST aggressive anti-bot detection among all Indian
    marketplaces. Requires:
    - Indian residential proxies (mandatory)
    - Playwright with stealth for all pages
    - Very conservative rate limiting
    - Session cookie persistence

    Data in __NEXT_DATA__ or __INITIAL_STATE__.
    JSON-LD on product pages as fallback.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "meesho"
    allowed_domains = ["meesho.com", "www.meesho.com"]

    QUICK_MODE_CATEGORIES = 4

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 4,
        "CONCURRENT_REQUESTS": 3,
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
            f"Meesho spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"failed={self.items_failed}"
        )

    async def _apply_stealth(self, page, request):
        try:
            await self.STEALTH.apply_stealth_async(page)
            page.set_default_navigation_timeout(90000)
            page.set_default_timeout(60000)
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
                        PageMethod("wait_for_timeout", random.randint(4000, 7000)),
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
            if self._max_pages_override <= 2:
                return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS[:self.QUICK_MODE_CATEGORIES]]
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    def _resolve_category_from_url(self, url: str) -> str | None:
        path = url.split("/pl/")[0].split("/")[-1].lower() if "/pl/" in url else ""
        if path in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[path]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in url.lower():
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
        if response.status in (403, 429, 503):
            return True
        if len(response.text) < 500:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        return "access denied" in title or "blocked" in title or "verification" in title

    def _extract_state(self, response) -> dict | None:
        """Extract __NEXT_DATA__ or __INITIAL_STATE__."""
        # Try __NEXT_DATA__ first (Meesho uses Next.js)
        script = response.css('script#__NEXT_DATA__::text').get()
        if script:
            try:
                return json.loads(script)
            except (json.JSONDecodeError, ValueError):
                pass

        # Fallback: regex search
        for pattern in [
            r'<script\s+id="__NEXT_DATA__"[^>]*>\s*(\{.+?\})\s*</script>',
            r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})\s*;?\s*</script>",
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

        state = self._extract_state(response)
        products = []
        if state:
            page_props = state.get("props", {}).get("pageProps") or state
            for key in ("catalogData", "products", "searchData", "data"):
                section = page_props.get(key) or {}
                prod_list = (
                    section.get("products")
                    or section.get("catalogs")
                    or section.get("items")
                    or section.get("results")
                    or []
                )
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(f"Found {len(products)} products on {response.url}")
            for prod in products:
                prod_id = prod.get("product_id") or prod.get("id") or prod.get("productId")
                if not prod_id:
                    continue
                product_url = f"https://www.meesho.com/p/{prod_id}"

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
                            PageMethod("wait_for_timeout", random.randint(3000, 5000)),
                        ],
                    },
                )
        else:
            # HTML fallback
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
                                PageMethod("wait_for_timeout", random.randint(3000, 5000)),
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
            next_url = f"{base_url}{separator}page={next_page}"
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
                        PageMethod("wait_for_timeout", random.randint(4000, 7000)),
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

        # Strategy 1: State data
        state = self._extract_state(response)
        if state:
            page_props = state.get("props", {}).get("pageProps") or state
            product = page_props.get("productData") or page_props.get("product") or page_props.get("data") or {}
            if product and (product.get("name") or product.get("product_name")):
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
                seller_name="Meesho", seller_rating=None,
                in_stock="OutOfStock" not in (offers.get("availability") or ""),
                fulfilled_by="Meesho", category_slug=category_slug, about_bullets=[],
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
        name = data.get("name") or data.get("product_name")
        if not name:
            return None

        pid = external_id or str(data.get("product_id") or data.get("id") or data.get("productId") or "")
        if not pid:
            return None

        selling_price = self._parse_price(
            data.get("price") or data.get("min_catalog_price") or data.get("discounted_price")
        )
        mrp = self._parse_price(
            data.get("mrp") or data.get("original_price") or data.get("max_catalog_price")
        )

        brand = data.get("brand") or data.get("brandName")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = []
        for key in ("images", "product_images", "imageUrls", "catalogImages"):
            img_list = data.get(key) or []
            for img in img_list:
                if isinstance(img, str):
                    images.append(img)
                elif isinstance(img, dict):
                    images.append(img.get("url") or img.get("src", ""))
        if not images:
            img = data.get("image") or data.get("product_image")
            if img and isinstance(img, str):
                images = [img]

        rating = None
        review_count = None
        if data.get("rating") or data.get("average_rating"):
            try:
                rating = Decimal(str(data.get("rating") or data.get("average_rating")))
            except (InvalidOperation, ValueError):
                pass
        if data.get("review_count") or data.get("total_ratings"):
            try:
                review_count = int(data.get("review_count") or data.get("total_ratings"))
            except (ValueError, TypeError):
                pass

        # Seller
        seller = data.get("supplier") or data.get("seller") or {}
        seller_name = seller.get("name") if isinstance(seller, dict) else "Meesho"

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
            seller_name=seller_name if seller_name else "Meesho",
            seller_rating=None,
            in_stock=data.get("in_stock", True),
            fulfilled_by="Meesho",
            category_slug=category_slug,
            about_bullets=[],
            offer_details=[],
            raw_html_path=None,
            description=data.get("description") or data.get("product_description"),
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
