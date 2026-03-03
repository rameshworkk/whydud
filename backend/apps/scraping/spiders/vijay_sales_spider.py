"""Vijay Sales spider — scrapes product listings and detail pages.

Architecture:
  Vijay Sales runs on Magento 2 with Unbxd search integration.
  - Listing pages: Server-rendered HTML with product cards
  - Detail pages: JSON-LD Product schema + HTML extraction
  - Playwright for JS-heavy pages where HTTP returns incomplete data

URL patterns:
  Category: /{category}/{subcategory}/c?page={n}
  Product:  /{product-slug}.html or /{product-slug}
  Search:   /catalogsearch/result/?q={keyword}
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

PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

MARKETPLACE_SLUG = "vijay-sales"

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Smartphones
    "mobiles": "smartphones",
    "smartphones": "smartphones",
    "mobile-phones": "smartphones",
    "mobile phones": "smartphones",
    "mobile accessories": "smartphones",
    "power banks": "smartphones",
    "tablets": "tablets",
    # Laptops & Computers
    "laptops": "laptops",
    "gaming laptops": "laptops",
    "notebook": "laptops",
    "desktops": "laptops",
    "monitors": "laptops",
    "printers": "laptops",
    "networking": "laptops",
    "storage": "laptops",
    "pen drives": "laptops",
    # Audio
    "headphones": "audio",
    "earphones": "audio",
    "earbuds": "audio",
    "bluetooth speakers": "audio",
    "soundbars": "audio",
    "home theatre": "audio",
    "party speakers": "audio",
    # Wearables
    "smartwatches": "smartwatches",
    "smart watches": "smartwatches",
    "fitness bands": "smartwatches",
    # Cameras
    "cameras": "cameras",
    "action cameras": "cameras",
    "dslr": "cameras",
    "mirrorless": "cameras",
    # TVs
    "televisions": "televisions",
    "led tv": "televisions",
    "smart tv": "televisions",
    "oled tv": "televisions",
    "projectors": "televisions",
    # Large Appliances
    "refrigerators": "refrigerators",
    "washing machines": "washing-machines",
    "air conditioners": "air-conditioners",
    "microwave": "appliances",
    "dishwashers": "appliances",
    "water heaters": "appliances",
    "geysers": "appliances",
    "chimneys": "appliances",
    # Small Appliances
    "air purifiers": "appliances",
    "water purifiers": "appliances",
    "vacuum cleaners": "appliances",
    "fans": "appliances",
    "irons": "appliances",
    "room heaters": "appliances",
    # Kitchen
    "mixer grinders": "kitchen-tools",
    "air fryers": "kitchen-tools",
    "coffee machines": "kitchen-tools",
    "induction cooktops": "kitchen-tools",
    "electric kettles": "kitchen-tools",
    "juicers": "kitchen-tools",
    "food processors": "kitchen-tools",
    "oven toaster": "kitchen-tools",
    "gas stoves": "kitchen-tools",
    # Personal Care
    "trimmers": "grooming",
    "shavers": "grooming",
    "hair dryers": "grooming",
    "hair straighteners": "grooming",
    # Gaming
    "gaming": "gaming",
    "gaming consoles": "gaming",
    "gaming accessories": "gaming",
}

# ---------------------------------------------------------------------------
# Seed URLs — Vijay Sales category pages
# Format: (url, max_pages)
# ---------------------------------------------------------------------------

_TOP = 15
_STD = 8

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones ─────────────────────────────────────────────────────
    ("https://www.vijaysales.com/mobiles-tablets/mobiles/c", _TOP),
    ("https://www.vijaysales.com/mobiles-tablets/tablets/c", _STD),
    # ── Laptops & Computers ─────────────────────────────────────────────
    ("https://www.vijaysales.com/computers/laptops/c", _TOP),
    ("https://www.vijaysales.com/computers/desktops/c", _STD),
    ("https://www.vijaysales.com/computers/monitors/c", _STD),
    ("https://www.vijaysales.com/computers/printers/c", _STD),
    # ── TVs ─────────────────────────────────────────────────────────────
    ("https://www.vijaysales.com/televisions/led-tv/c", _TOP),
    ("https://www.vijaysales.com/televisions/projectors/c", _STD),
    # ── Audio ───────────────────────────────────────────────────────────
    ("https://www.vijaysales.com/audio-video/headphones-earphones/c", _TOP),
    ("https://www.vijaysales.com/audio-video/bluetooth-speakers/c", _STD),
    ("https://www.vijaysales.com/audio-video/soundbars-home-theatre/c", _STD),
    # ── Wearables ───────────────────────────────────────────────────────
    ("https://www.vijaysales.com/mobiles-tablets/smartwatches/c", _TOP),
    # ── Cameras ─────────────────────────────────────────────────────────
    ("https://www.vijaysales.com/cameras/digital-cameras/c", _STD),
    # ── Large Appliances ────────────────────────────────────────────────
    ("https://www.vijaysales.com/home-appliances/refrigerators/c", _TOP),
    ("https://www.vijaysales.com/home-appliances/washing-machines/c", _TOP),
    ("https://www.vijaysales.com/home-appliances/air-conditioners/c", _TOP),
    ("https://www.vijaysales.com/home-appliances/microwave-ovens/c", _STD),
    ("https://www.vijaysales.com/home-appliances/dishwashers/c", _STD),
    # ── Small Appliances ────────────────────────────────────────────────
    ("https://www.vijaysales.com/home-appliances/air-purifiers/c", _STD),
    ("https://www.vijaysales.com/home-appliances/water-purifiers/c", _STD),
    ("https://www.vijaysales.com/home-appliances/vacuum-cleaners/c", _STD),
    # ── Kitchen Appliances ──────────────────────────────────────────────
    ("https://www.vijaysales.com/kitchen-appliances/mixer-grinders/c", _STD),
    ("https://www.vijaysales.com/kitchen-appliances/air-fryers/c", _STD),
    ("https://www.vijaysales.com/kitchen-appliances/electric-kettles/c", _STD),
    ("https://www.vijaysales.com/kitchen-appliances/induction-cooktops/c", _STD),
    # ── Personal Care ───────────────────────────────────────────────────
    ("https://www.vijaysales.com/personal-care/trimmers-shavers/c", _STD),
    ("https://www.vijaysales.com/personal-care/hair-dryers-straighteners/c", _STD),
    # ── Gaming ──────────────────────────────────────────────────────────
    ("https://www.vijaysales.com/gaming/gaming-consoles/c", _STD),
    ("https://www.vijaysales.com/gaming/gaming-accessories/c", _STD),
]

MAX_LISTING_PAGES = 5


class VijaySalesSpider(BaseWhydudSpider):
    """Scrapes VijayS ales.com electronics store.

    Vijay Sales runs on Magento 2 with server-rendered category pages
    and product detail pages. JSON-LD Product schema is available on
    detail pages for structured extraction.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES.
    """

    name = "vijay_sales"
    allowed_domains = ["vijaysales.com", "www.vijaysales.com"]

    QUICK_MODE_CATEGORIES = 6

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
            f"Vijay Sales spider finished ({reason}): "
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
    # start_requests
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
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories")

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
            if keyword.replace(" ", "-") in path:
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
        """Detect if site served a block/error page."""
        if response.status in (403, 429):
            return True
        title = (response.css("title::text").get() or "").strip().lower()
        if "access denied" in title or "blocked" in title or "service unavailable" in title:
            return True
        return False

    # ------------------------------------------------------------------
    # Phase 1: Listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from category listing page."""
        self._listing_pages_scraped += 1

        if self._is_blocked(response):
            self.logger.warning(f"Blocked on listing {response.url} — skipping")
            return

        category_slug = response.meta.get("category_slug")

        # Extract product links from listing page
        # Vijay Sales uses various card selectors depending on page type
        product_links = set()

        # Try multiple product card selectors
        selectors = [
            "a.product-item-link::attr(href)",
            "a.product-card-link::attr(href)",
            ".product-item a::attr(href)",
            ".product-card a::attr(href)",
            "a[href*='.html']::attr(href)",
            ".products-grid a::attr(href)",
            "li.product-item a.product-item-photo::attr(href)",
            ".product-listing a::attr(href)",
        ]

        for sel in selectors:
            for href in response.css(sel).getall():
                full_url = response.urljoin(href)
                # Filter for product URLs (typically end in .html or have product-like paths)
                if self._is_product_url(full_url):
                    product_links.add(full_url)

        if product_links:
            self.logger.info(f"Found {len(product_links)} products on {response.url}")
            for prod_url in product_links:
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
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                        PageMethod("wait_for_timeout", 3000),
                    ],
                },
            )

    def _is_product_url(self, url: str) -> bool:
        """Check if URL looks like a product detail page."""
        # Vijay Sales product URLs typically end in .html
        # and contain the domain
        if "vijaysales.com" not in url:
            return False
        path = url.split("?")[0].lower()
        # Exclude category, search, and non-product pages
        exclude_patterns = ["/c", "/catalogsearch", "/checkout", "/customer", "/wishlist"]
        for pattern in exclude_patterns:
            if path.endswith(pattern) or f"{pattern}/" in path:
                return False
        # Product pages typically end in .html or have a product-like slug
        if path.endswith(".html"):
            return True
        return False

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

        # Strategy 1: JSON-LD
        item = self._parse_from_json_ld(response, category_slug)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        # Strategy 2: HTML extraction
        item = self._parse_from_html(response, category_slug)
        if item:
            self._product_pages_scraped += 1
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
            return

        self.logger.warning(f"Could not extract product data from {response.url}")
        self.items_failed += 1

    # ------------------------------------------------------------------
    # Extraction: JSON-LD (primary)
    # ------------------------------------------------------------------

    def _parse_from_json_ld(
        self, response, category_slug: str | None,
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

            sku = ld_data.get("sku") or ld_data.get("productID")
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

            description = ld_data.get("description")

            return ProductItem(
                marketplace_slug=MARKETPLACE_SLUG,
                external_id=str(sku),
                url=response.url,
                title=name,
                brand=brand,
                price=price,
                mrp=None,  # JSON-LD typically has selling price only
                images=images,
                rating=rating,
                review_count=review_count,
                specs={},
                seller_name="Vijay Sales",
                seller_rating=None,
                in_stock=in_stock,
                fulfilled_by="Vijay Sales",
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
        return None

    # ------------------------------------------------------------------
    # Extraction: HTML (fallback)
    # ------------------------------------------------------------------

    def _parse_from_html(
        self, response, category_slug: str | None,
    ) -> ProductItem | None:
        """Extract product data from HTML elements."""
        # Title
        title = response.css(
            "h1.page-title span::text, h1.product-name::text, "
            "h1.product-title::text, .product-info-main h1::text"
        ).get()
        if not title:
            return None
        title = title.strip()

        # SKU
        sku = response.css(
            "div.product-sku::text, span.product-sku::text, "
            "[itemprop='sku']::text, .sku .value::text"
        ).get()
        if not sku:
            # Try to extract from URL
            sku = re.sub(r"[^a-zA-Z0-9-]", "", response.url.split("/")[-1].replace(".html", ""))
        if not sku:
            return None
        sku = sku.strip()

        # Selling price
        price_text = response.css(
            "span.price::text, span.special-price .price::text, "
            ".product-info-price .price::text, [data-price-type='finalPrice'] .price::text"
        ).get()
        price = self._parse_price(price_text)

        # MRP
        mrp_text = response.css(
            "span.old-price .price::text, .product-info-price .old-price .price::text, "
            "[data-price-type='oldPrice'] .price::text"
        ).get()
        mrp = self._parse_price(mrp_text)

        # Brand
        brand = response.css(
            "span.product-brand::text, div.brand-name::text, "
            ".product-brand a::text, [itemprop='brand']::text"
        ).get()

        # Images
        images = []
        for img_sel in [
            "img.gallery-placeholder__image::attr(src)",
            ".product-image-photo::attr(src)",
            ".fotorama img::attr(src)",
            "img[itemprop='image']::attr(src)",
        ]:
            for img in response.css(img_sel).getall():
                if img and not img.startswith("data:"):
                    images.append(response.urljoin(img))

        # Specs
        specs = {}
        for row in response.css("table.additional-attributes tr, .product-attributes tr"):
            key = row.css("th::text, td.label::text").get()
            val = row.css("td.data::text, td.value::text").get()
            if key and val:
                specs[key.strip()] = val.strip()

        # Breadcrumbs
        breadcrumbs = [
            bc.strip()
            for bc in response.css(".breadcrumbs li a::text, .breadcrumbs li span::text").getall()
            if bc.strip()
        ]

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=sku,
            url=response.url,
            title=title,
            brand=brand.strip() if brand else None,
            price=price,
            mrp=mrp,
            images=images,
            rating=None,
            review_count=None,
            specs=specs,
            seller_name="Vijay Sales",
            seller_rating=None,
            in_stock=True,
            fulfilled_by="Vijay Sales",
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
            manufacturer=specs.get("Manufacturer") or (brand.strip() if brand else None),
            model_number=specs.get("Model Number") or specs.get("Model Name"),
            weight=specs.get("Weight") or specs.get("Product Weight"),
            dimensions=specs.get("Dimensions") or specs.get("Product Dimensions"),
        )
