"""Myntra spider — scrapes fashion marketplace listings and details.

Architecture:
  Myntra is a React SPA with sophisticated anti-bot (fingerprinting + behavior).
  - Data source: window.__myx (React app state) or API responses
  - JSON-LD on product pages
  - Playwright required for all pages (SPA, no SSR product data)

URL patterns:
  Category: /{category}?p={page}&sort=popularity
  Product:  /{product-slug}/{product-id}
  Search:   /{search-term}
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

PRODUCT_ID_RE = re.compile(r"/(\d{5,})(?:\?|$)")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "myntra"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Men
    "men-tshirts": "mens-fashion",
    "men-shirts": "mens-fashion",
    "men-jeans": "mens-fashion",
    "men-trousers": "mens-fashion",
    "men-shorts": "mens-fashion",
    "men-jackets": "mens-fashion",
    "men-sweaters": "mens-fashion",
    "men-kurtas": "mens-fashion",
    "men-track-pants": "mens-fashion",
    "men-innerwear": "mens-fashion",
    # Women
    "women-kurtas-kurtis": "womens-fashion",
    "women-tops": "womens-fashion",
    "women-dresses": "womens-fashion",
    "women-jeans": "womens-fashion",
    "women-sarees": "womens-fashion",
    "women-leggings": "womens-fashion",
    "women-ethnic-wear": "womens-fashion",
    "women-western-wear": "womens-fashion",
    "women-nightwear": "womens-fashion",
    # Kids
    "kids-clothing": "kids-fashion",
    "boys-clothing": "kids-fashion",
    "girls-clothing": "kids-fashion",
    # Footwear
    "men-casual-shoes": "footwear",
    "men-sports-shoes": "footwear",
    "men-formal-shoes": "footwear",
    "men-sandals": "footwear",
    "women-flats": "footwear",
    "women-heels": "footwear",
    "women-sneakers": "footwear",
    "sports-shoes": "footwear",
    # Accessories
    "men-watches": "watches",
    "women-watches": "watches",
    "sunglasses": "accessories",
    "bags-backpacks": "accessories",
    "belts": "accessories",
    "wallets": "accessories",
    "jewellery": "jewellery",
    # Beauty
    "lipstick": "makeup",
    "foundation": "makeup",
    "nail-polish": "makeup",
    "makeup": "makeup",
    "skincare": "skincare",
    "haircare": "hair-care",
    "fragrance": "fragrance",
    "bath-body": "bath-body",
}

# ---------------------------------------------------------------------------
# Seed URLs
# ---------------------------------------------------------------------------

_TOP = 10
_STD = 5

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Men ─────────────────────────────────────────────────────────────
    ("https://www.myntra.com/men-tshirts", _TOP),
    ("https://www.myntra.com/men-shirts", _STD),
    ("https://www.myntra.com/men-jeans", _STD),
    ("https://www.myntra.com/men-trousers", _STD),
    ("https://www.myntra.com/men-jackets", _STD),
    ("https://www.myntra.com/men-kurtas", _STD),
    # ── Women ───────────────────────────────────────────────────────────
    ("https://www.myntra.com/women-kurtas-kurtis-suits", _TOP),
    ("https://www.myntra.com/women-tops-t-shirts", _STD),
    ("https://www.myntra.com/women-dresses", _STD),
    ("https://www.myntra.com/women-sarees", _STD),
    ("https://www.myntra.com/women-jeans", _STD),
    # ── Kids ────────────────────────────────────────────────────────────
    ("https://www.myntra.com/kids-clothing", _STD),
    # ── Footwear ────────────────────────────────────────────────────────
    ("https://www.myntra.com/men-casual-shoes", _TOP),
    ("https://www.myntra.com/men-sports-shoes", _STD),
    ("https://www.myntra.com/women-flats", _STD),
    ("https://www.myntra.com/women-heels", _STD),
    ("https://www.myntra.com/sports-shoes", _STD),
    # ── Watches & Accessories ───────────────────────────────────────────
    ("https://www.myntra.com/men-watches", _STD),
    ("https://www.myntra.com/women-watches", _STD),
    ("https://www.myntra.com/sunglasses", _STD),
    ("https://www.myntra.com/bags-backpacks", _STD),
    # ── Beauty ──────────────────────────────────────────────────────────
    ("https://www.myntra.com/lipstick", _STD),
    ("https://www.myntra.com/foundation", _STD),
    ("https://www.myntra.com/skincare", _STD),
    ("https://www.myntra.com/haircare", _STD),
    ("https://www.myntra.com/fragrance-for-men", _STD),
]

MAX_LISTING_PAGES = 5


class MyntraSpider(BaseWhydudSpider):
    """Scrapes Myntra.com fashion marketplace.

    Myntra is a React SPA with advanced anti-bot detection.
    Playwright required for ALL pages. Data in window.__myx state
    or rendered HTML after JS execution.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "myntra"
    allowed_domains = ["myntra.com", "www.myntra.com"]

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
            f"Myntra spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
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

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

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
        path = url.split("?")[0].split("/")[-1].lower()
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
        if response.status in (403, 429):
            return True
        if len(response.text) < 500:
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        return "access denied" in title or "blocked" in title

    def _extract_myx_state(self, response) -> dict | None:
        """Extract window.__myx React app state."""
        match = re.search(
            r"window\.__myx\s*=\s*(\{.+?\})\s*;?\s*</script>",
            response.text,
            re.DOTALL,
        )
        if not match:
            return None
        try:
            return json.loads(match.group(1))
        except (json.JSONDecodeError, ValueError):
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

        # Strategy 1: __myx state
        state = self._extract_myx_state(response)
        products = []
        if state:
            for key in ("searchData", "products", "results"):
                section = state.get(key) or {}
                prod_list = section.get("results") or section.get("products") or section.get("items") or []
                if isinstance(prod_list, list) and prod_list:
                    products = prod_list
                    break

        if products:
            self.logger.info(f"Found {len(products)} products (state) on {response.url}")
            for prod in products:
                prod_id = prod.get("productId") or prod.get("id")
                slug = prod.get("landingPageUrl") or prod.get("url") or ""
                if not prod_id:
                    continue
                if slug.startswith("/"):
                    product_url = f"https://www.myntra.com{slug}"
                else:
                    product_url = f"https://www.myntra.com/{prod_id}"

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
            # Strategy 2: HTML product cards
            links = set()
            for card in response.css("li.product-base a::attr(href), a[href*='/buy/']::attr(href)").getall():
                full = response.urljoin(card)
                if re.search(r"/\d{5,}", full):
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
            next_url = f"{base_url}?p={next_page}&sort=popularity"
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

        # Strategy 1: __myx state
        state = self._extract_myx_state(response)
        if state:
            pdp = state.get("pdpData") or state.get("productData") or state.get("product") or {}
            if pdp.get("name") or pdp.get("productName"):
                item = self._parse_from_state(pdp, response.url, category_slug, external_id)
                if item:
                    self._product_pages_scraped += 1
                    self.items_scraped += 1
                    yield item
                    return

        # Strategy 2: JSON-LD
        item = self._parse_from_json_ld(response, category_slug, external_id)
        if item:
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 3: HTML
        item = self._parse_from_html(response, category_slug, external_id)
        if item:
            self._product_pages_scraped += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 4: Listing data
        if listing_data:
            item = self._parse_from_listing(listing_data, response.url, category_slug, external_id)
            if item:
                self._product_pages_scraped += 1
                self.items_scraped += 1
                yield item
                return

        self.logger.warning(f"Could not extract from {response.url}")
        self.items_failed += 1

    def _parse_from_state(self, pdp: dict, url: str, category_slug: str | None, external_id: str | None) -> ProductItem | None:
        name = pdp.get("name") or pdp.get("productName")
        if not name:
            return None

        pid = external_id or str(pdp.get("id") or pdp.get("productId") or "")
        if not pid:
            return None

        price_data = pdp.get("price") or pdp.get("sizes", [{}])[0] if isinstance(pdp.get("sizes"), list) else {}
        selling_price = self._parse_price(pdp.get("discountedPrice") or pdp.get("price") or (price_data.get("discountedPrice") if isinstance(price_data, dict) else None))
        mrp = self._parse_price(pdp.get("mrp") or (price_data.get("mrp") if isinstance(price_data, dict) else None))

        brand = pdp.get("brand") or pdp.get("brandName")
        if isinstance(brand, dict):
            brand = brand.get("name")

        images = []
        for img in pdp.get("media", {}).get("images", []) if isinstance(pdp.get("media"), dict) else []:
            if isinstance(img, dict):
                images.append(img.get("src") or img.get("url", ""))
            elif isinstance(img, str):
                images.append(img)
        if not images:
            for img in pdp.get("images") or pdp.get("imageUrls") or []:
                if isinstance(img, str):
                    images.append(img)

        rating = None
        review_count = None
        ratings = pdp.get("ratings") or pdp.get("rating") or {}
        if isinstance(ratings, dict):
            if ratings.get("averageRating"):
                try:
                    rating = Decimal(str(ratings["averageRating"]))
                except (InvalidOperation, ValueError):
                    pass
            if ratings.get("totalCount"):
                try:
                    review_count = int(ratings["totalCount"])
                except (ValueError, TypeError):
                    pass

        description = pdp.get("productDescription") or pdp.get("description")

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
            seller_name="Myntra",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Myntra",
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

    def _parse_from_json_ld(self, response, category_slug, external_id) -> ProductItem | None:
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
            price = self._parse_price(offers.get("price"))
            brand_data = ld.get("brand") or {}
            brand = brand_data.get("name") if isinstance(brand_data, dict) else str(brand_data) if brand_data else None
            images = ld.get("image") or []
            if isinstance(images, str):
                images = [images]

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG, external_id=str(sku), url=response.url,
                title=name, brand=brand, price=price, mrp=None, images=images,
                rating=None, review_count=None, specs={}, seller_name="Myntra",
                seller_rating=None, in_stock="OutOfStock" not in (offers.get("availability") or ""),
                fulfilled_by="Myntra", category_slug=category_slug, about_bullets=[],
                offer_details=[], raw_html_path=None, description=ld.get("description"),
                warranty=None, delivery_info=None, return_policy=None, breadcrumbs=[],
                variant_options=[], country_of_origin=None, manufacturer=brand,
                model_number=None, weight=None, dimensions=None,
            )
        return None

    def _parse_from_html(self, response, category_slug, external_id) -> ProductItem | None:
        title = response.css("h1.pdp-title::text, h1.pdp-name::text, h1::text").get()
        if not title:
            return None

        pid = external_id
        if not pid:
            return None

        price_text = response.css("span.pdp-price strong::text, span.pdp-discount-container span::text").get()
        price = self._parse_price(price_text)
        mrp_text = response.css("span.pdp-mrp s::text, span.pdp-price span.pdp-mrp::text").get()
        mrp = self._parse_price(mrp_text)
        brand = response.css("h1.pdp-title .pdp-title-brand::text, .pdp-name .pdp-brand::text").get()

        images = response.css("div.image-grid-image::attr(style), img.pdp-image::attr(src)").getall()
        clean_images = []
        for img in images:
            if "url(" in img:
                match = re.search(r'url\(["\']?(.+?)["\']?\)', img)
                if match:
                    clean_images.append(match.group(1))
            elif img and not img.startswith("data:"):
                clean_images.append(img)

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG, external_id=pid, url=response.url,
            title=title.strip(), brand=brand.strip() if brand else None, price=price, mrp=mrp,
            images=clean_images, rating=None, review_count=None, specs={},
            seller_name="Myntra", seller_rating=None, in_stock=True, fulfilled_by="Myntra",
            category_slug=category_slug, about_bullets=[], offer_details=[],
            raw_html_path=None, description=None, warranty=None, delivery_info=None,
            return_policy=None, breadcrumbs=[], variant_options=[], country_of_origin=None,
            manufacturer=None, model_number=None, weight=None, dimensions=None,
        )

    def _parse_from_listing(self, listing, url, category_slug, external_id) -> ProductItem | None:
        name = listing.get("productName") or listing.get("name")
        pid = external_id or str(listing.get("productId") or listing.get("id") or "")
        if not name or not pid:
            return None

        price = self._parse_price(listing.get("discountedPrice") or listing.get("price"))
        mrp = self._parse_price(listing.get("mrp"))
        brand = listing.get("brand") or listing.get("brandName")
        images = []
        for img in listing.get("images") or listing.get("searchImage") or []:
            if isinstance(img, str):
                images.append(img)
            elif isinstance(img, dict):
                images.append(img.get("src", ""))

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG, external_id=pid, url=url,
            title=name, brand=brand, price=price, mrp=mrp, images=[i for i in images if i],
            rating=None, review_count=None, specs={}, seller_name="Myntra",
            seller_rating=None, in_stock=True, fulfilled_by="Myntra",
            category_slug=category_slug, about_bullets=[], offer_details=[],
            raw_html_path=None, description=None, warranty=None, delivery_info=None,
            return_policy=None, breadcrumbs=[], variant_options=[], country_of_origin=None,
            manufacturer=brand, model_number=None, weight=None, dimensions=None,
        )
