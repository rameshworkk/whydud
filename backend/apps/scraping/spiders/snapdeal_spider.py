"""Snapdeal spider — two-phase: search listing HTML + product detail microdata.

Architecture:
  Phase 1 (Listing): HTTP GET to search pages, parse product cards from
    .product-tuple-listing elements. Pagination via offset query param.
  Phase 2 (Detail): HTTP GET to product pages, extract structured data
    from schema.org microdata (itemprop attributes). Falls back to hidden
    inputs + CSS selectors when microdata is sparse.

  No Playwright needed — Snapdeal is fully server-rendered HTML.
  Zero anti-bot (AWS CloudFront caching only, no WAF).

  Prices on Snapdeal are in RUPEES (not paisa). Spider converts to paisa
  (* 100) before yielding.

CRITICAL: /honeybot is a honeypot link — spider MUST NOT follow it.

URL patterns:
  Search:  /search?keyword={term}&noOfResults=20&offset={N}
  Product: /product/{slug}/{pogId}  (slug IS required — pogId alone 404s)
"""
import random
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote_plus

import scrapy

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MARKETPLACE_SLUG = "snapdeal"

SEARCH_BASE = "https://www.snapdeal.com/search"
RESULTS_PER_PAGE = 20

POG_ID_RE = re.compile(r"/product/[^/]+/(\d+)")
SLUG_RE = re.compile(r"/product/([^/]+)/\d+")
PRICE_RE = re.compile(r"[\d,]+(?:\.\d{1,2})?")

# ---------------------------------------------------------------------------
# Seed queries — (search_query, category_slug_hint, max_pages)
# ---------------------------------------------------------------------------

SEED_QUERIES: list[tuple[str, str, int]] = [
    # ── Electronics ──────────────────────────────────────────────────────
    ("smartphones", "smartphones", 10),
    ("laptops", "laptops", 10),
    ("headphones", "audio", 5),
    ("earbuds", "audio", 5),
    ("tablets", "tablets", 5),
    ("televisions", "televisions", 5),
    ("cameras", "cameras", 5),
    # ── Home Appliances ──────────────────────────────────────────────────
    ("air conditioners", "air-conditioners", 5),
    ("refrigerators", "refrigerators", 5),
    ("washing machines", "washing-machines", 5),
    ("air purifiers", "appliances", 5),
    ("vacuum cleaners", "appliances", 3),
    # ── Kitchen ──────────────────────────────────────────────────────────
    ("mixer grinders", "kitchen-tools", 3),
    ("induction cooktops", "kitchen-tools", 3),
    # ── Personal Care ────────────────────────────────────────────────────
    ("trimmers", "grooming", 3),
    ("shavers", "grooming", 3),
    # ── Watches & Wearables ──────────────────────────────────────────────
    ("smartwatches", "smartwatches", 5),
]

# ---------------------------------------------------------------------------
# Keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    "smartphones": "smartphones",
    "smart phones": "smartphones",
    "mobiles": "smartphones",
    "mobile phones": "smartphones",
    "laptops": "laptops",
    "notebooks": "laptops",
    "headphones": "audio",
    "earphones": "audio",
    "earbuds": "audio",
    "speakers": "audio",
    "bluetooth speakers": "audio",
    "soundbars": "audio",
    "televisions": "televisions",
    "tvs": "televisions",
    "led tv": "televisions",
    "smart tv": "televisions",
    "air conditioners": "air-conditioners",
    "split ac": "air-conditioners",
    "refrigerators": "refrigerators",
    "fridge": "refrigerators",
    "washing machines": "washing-machines",
    "air purifiers": "appliances",
    "vacuum cleaners": "appliances",
    "water purifiers": "appliances",
    "cameras": "cameras",
    "dslr": "cameras",
    "tablets": "tablets",
    "smartwatches": "smartwatches",
    "smart watches": "smartwatches",
    "gaming": "gaming",
    "printers": "laptops",
    "monitors": "laptops",
    "mixer grinders": "kitchen-tools",
    "induction cooktops": "kitchen-tools",
    "kitchen appliances": "kitchen-tools",
    "trimmers": "grooming",
    "shavers": "grooming",
}


class SnapdealSpider(BaseWhydudSpider):
    """Scrapes Snapdeal.com via search HTML + product page microdata.

    Two-phase architecture — no Playwright required:
      Phase 1: Parse search result HTML for product URLs + basic data
      Phase 2: Parse product detail pages via schema.org microdata

    Prices on Snapdeal are in INR (rupees), NOT paisa. Spider converts.

    CRITICAL: /honeybot is a honeypot link — NEVER followed.

    Spider arguments:
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override search terms or product URLs.
      max_pages     — override max pages per query.
    """

    name = "snapdeal"
    allowed_domains = ["snapdeal.com", "www.snapdeal.com"]

    QUICK_MODE_QUERIES = 4

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 2,
        "RANDOMIZE_DOWNLOAD_DELAY": True,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
        "HTTPERROR_ALLOWED_CODES": [403, 429],
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
        self._override_queries: list[str] = (
            [u.strip() for u in category_urls.split(",") if u.strip()]
            if category_urls
            else []
        )
        self._max_pages_override: int | None = int(max_pages) if max_pages else None

        # Dedup — track seen pogIds to avoid duplicate detail requests
        self._seen_ids: set[str] = set()

        # Stats
        self._listing_pages_fetched: int = 0
        self._product_pages_fetched: int = 0
        self._products_extracted: int = 0
        self._duplicates_skipped: int = 0

    def closed(self, reason: str) -> None:
        """Log final scrape statistics."""
        self.logger.info(
            f"Snapdeal spider finished ({reason}): "
            f"listing_pages={self._listing_pages_fetched}, "
            f"product_pages={self._product_pages_fetched}, "
            f"products_extracted={self._products_extracted}, "
            f"duplicates_skipped={self._duplicates_skipped}, "
            f"items_scraped={self.items_scraped}, "
            f"items_failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # Request helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_search_url(query: str, offset: int = 0) -> str:
        """Construct a Snapdeal search URL."""
        q = quote_plus(query)
        return f"{SEARCH_BASE}?keyword={q}&noOfResults={RESULTS_PER_PAGE}&offset={offset}"

    # ------------------------------------------------------------------
    # start_requests
    # ------------------------------------------------------------------

    def start_requests(self):
        """Emit HTTP requests for each seed search query."""
        queries = self._load_queries()
        random.shuffle(queries)

        for query, category_slug, max_pg in queries:
            url = self._build_search_url(query, offset=0)
            self.logger.info(f"Queuing search: '{query}' (max {max_pg} pages)")
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "query": query,
                    "current_page": 1,
                    "max_pages": max_pg,
                    "playwright": False,
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(queries)} seed queries")

    def _load_queries(self) -> list[tuple[str, str, int]]:
        """Resolve the (query, category_slug, max_pages) list to crawl."""
        fallback_max = self._max_pages_override or 5

        if self._override_queries:
            return [
                (q, self._resolve_category(q), fallback_max)
                for q in self._override_queries
            ]

        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob
                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        if self._max_pages_override is not None:
            if self._max_pages_override <= 2:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_QUERIES} queries "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (q, slug, self._max_pages_override)
                    for q, slug, _ in SEED_QUERIES[:self.QUICK_MODE_QUERIES]
                ]
            return [
                (q, slug, self._max_pages_override)
                for q, slug, _ in SEED_QUERIES
            ]

        return list(SEED_QUERIES)

    def _resolve_category(self, query: str) -> str:
        """Resolve a query string to a Whydud category slug."""
        q_lower = query.lower().strip()
        if q_lower in KEYWORD_CATEGORY_MAP:
            return KEYWORD_CATEGORY_MAP[q_lower]
        for keyword, slug in KEYWORD_CATEGORY_MAP.items():
            if keyword in q_lower or q_lower in keyword:
                return slug
        return ""

    # ------------------------------------------------------------------
    # Phase 1: Search listing pages
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Parse search results HTML for product links and basic data."""
        self._listing_pages_fetched += 1

        if response.status in (403, 429):
            self.logger.warning(
                f"Rate limited ({response.status}) on {response.url} — stopping query"
            )
            return

        category_slug = response.meta["category_slug"]
        query = response.meta["query"]
        current_page = response.meta["current_page"]
        max_pages = response.meta["max_pages"]

        # Extract product cards from .product-tuple-listing elements
        cards = response.css(".product-tuple-listing")
        product_count = 0

        for card in cards:
            # Get product URL — SKIP honeypot links
            href = card.css("a::attr(href)").get()
            if not href or "/product/" not in href:
                continue

            full_url = response.urljoin(href)

            # CRITICAL: Never follow /honeybot honeypot
            if "/honeybot" in full_url.lower():
                self.logger.debug(f"Skipped honeypot link: {full_url}")
                continue

            # Extract pogId from URL
            pog_match = POG_ID_RE.search(full_url)
            if not pog_match:
                continue
            pog_id = pog_match.group(1)

            # Dedup
            if pog_id in self._seen_ids:
                self._duplicates_skipped += 1
                continue
            self._seen_ids.add(pog_id)

            product_count += 1

            yield scrapy.Request(
                full_url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "pog_id": pog_id,
                    "playwright": False,
                },
            )

        self.logger.info(
            f"Query '{query}' page {current_page}: "
            f"{len(cards)} cards, {product_count} new products"
        )

        # No products means we've exhausted results — stop pagination
        if product_count == 0:
            return

        # Pagination — increment offset by RESULTS_PER_PAGE (20)
        if current_page < max_pages:
            next_page = current_page + 1
            next_offset = (next_page - 1) * RESULTS_PER_PAGE
            next_url = self._build_search_url(query, offset=next_offset)

            yield scrapy.Request(
                next_url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "category_slug": category_slug,
                    "query": query,
                    "current_page": next_page,
                    "max_pages": max_pages,
                    "playwright": False,
                },
                dont_filter=True,
            )

    # ------------------------------------------------------------------
    # Phase 2: Product detail pages
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data from detail page using schema.org microdata.

        Primary: itemprop attributes (most reliable on Snapdeal)
        Fallback: hidden inputs + CSS selectors
        """
        self._product_pages_fetched += 1

        if response.status in (403, 404, 429):
            self.logger.warning(
                f"Error {response.status} on product page {response.url}"
            )
            self.items_failed += 1
            return

        category_slug = response.meta.get("category_slug")
        pog_id = response.meta.get("pog_id")

        # Fallback pogId extraction from URL
        if not pog_id:
            pog_match = POG_ID_RE.search(response.url)
            pog_id = pog_match.group(1) if pog_match else None

        if not pog_id:
            self.logger.warning(f"No pogId for {response.url} — skipping")
            self.items_failed += 1
            return

        # Primary extraction: microdata + hidden inputs + CSS
        item = self._extract_product(response, category_slug, pog_id)
        if item:
            self._products_extracted += 1
            self.items_scraped += 1
            yield item
        else:
            self.logger.warning(f"Could not extract product data from {response.url}")
            self.items_failed += 1

    def _extract_product(
        self, response, category_slug: str | None, pog_id: str,
    ) -> ProductItem | None:
        """Extract product data combining microdata, hidden inputs, and CSS.

        Data sources (checked in priority order):
          1. itemprop microdata attributes (most reliable)
          2. Hidden input fields (#productPrice, #brandName, etc.)
          3. CSS selectors (h1, price elements)
          4. OG meta tags (last resort)
        """
        # === Title ===
        title = (
            response.css("[itemprop='name']::text").get()
            or response.css("input#productNamePDP::attr(value)").get()
            or response.css("h1::text").get()
            or response.css("meta[property='og:title']::attr(content)").get()
        )
        if not title or not title.strip():
            return None
        title = title.strip()

        # === Price (rupees → paisa) ===
        # itemprop="price" is the most reliable source
        price_str = (
            response.css("[itemprop='price']::attr(content)").get()
            or response.css("[itemprop='price']::text").get()
            or response.css("input#productPrice::attr(value)").get()
            or response.css("meta[property='og:price:amount']::attr(content)").get()
        )
        price = self._parse_price(price_str)

        # MRP (original/strikethrough price)
        mrp_str = response.css(".discount-price.strike::text").get()
        if not mrp_str:
            mrp_str = response.css(".original-price::text, .pdpCutPrice::text").get()
        mrp = self._parse_price(mrp_str)

        # === Brand ===
        brand = (
            response.css("[itemprop='brand']::text").get()
            or response.css("[itemprop='brand'] [itemprop='name']::text").get()
            or response.css("input#brandName::attr(value)").get()
            or response.css("a[href*='/brand/']::text").get()
        )
        if brand:
            brand = brand.strip() or None

        # === Rating ===
        rating = None
        rating_str = (
            response.css("[itemprop='ratingValue']::text").get()
            or response.css("[itemprop='ratingValue']::attr(content)").get()
            or response.css("input#avgRating::attr(value)").get()
        )
        if rating_str:
            try:
                rating = Decimal(rating_str.strip())
                if rating <= 0:
                    rating = None
            except (InvalidOperation, ValueError):
                pass

        # === Review count ===
        review_count = None
        review_str = (
            response.css("[itemprop='reviewCount']::text").get()
            or response.css("[itemprop='reviewCount']::attr(content)").get()
            or response.css("[itemprop='ratingCount']::text").get()
            or response.css("[itemprop='ratingCount']::attr(content)").get()
        )
        if review_str:
            try:
                review_count = int(re.sub(r"[^\d]", "", review_str.strip()))
                if review_count == 0:
                    review_count = None
            except (ValueError, TypeError):
                pass

        # === Currency verification ===
        currency = response.css("[itemprop='priceCurrency']::attr(content)").get()
        if currency and currency.strip().upper() != "INR":
            self.logger.warning(
                f"Unexpected currency {currency} on {response.url}"
            )

        # === Description ===
        description = (
            response.css("[itemprop='description']::text").get()
            or response.css("meta[property='og:description']::attr(content)").get()
        )
        if description:
            description = description.strip()[:5000] or None

        # === Availability / Stock ===
        availability = response.css("[itemprop='availability']::attr(content)").get()
        sold_out_input = response.css("input#soldOut::attr(value)").get()
        if availability:
            in_stock = "instock" in availability.lower()
        elif sold_out_input:
            in_stock = sold_out_input.strip().lower() != "true"
        else:
            # Check for sold-out indicators in page
            sold_out_el = response.css(".soldOutNotifyMe, .sold-out-text")
            in_stock = len(sold_out_el) == 0

        # === Images ===
        images = self._extract_images(response)

        # === Specifications ===
        specs = self._extract_specs(response)

        # === Seller ===
        seller_name = response.css(
            ".seller-details a::text, "
            "[itemprop='seller'] [itemprop='name']::text"
        ).get()
        if seller_name:
            seller_name = seller_name.strip()

        seller_rating = None
        seller_rating_str = response.css(
            ".seller-rating-count::text, .seller-details .rating::text"
        ).get()
        if seller_rating_str:
            try:
                seller_rating = Decimal(
                    re.sub(r"[^\d.]", "", seller_rating_str.strip())
                )
            except (InvalidOperation, ValueError):
                pass

        # === Breadcrumbs ===
        breadcrumbs = [
            bc.strip()
            for bc in response.css(
                ".bCrumbOmniTrack a::text, "
                ".bCrumbOmniTrack span::text, "
                "[itemtype*='BreadcrumbList'] [itemprop='name']::text"
            ).getall()
            if bc.strip()
        ]

        # === Warranty, Weight, Dimensions, Manufacturer, Model ===
        warranty = specs.get("Warranty") or specs.get("warranty")
        country_of_origin = specs.get("Country of Origin") or specs.get("Country Of Origin")
        manufacturer = specs.get("Manufacturer") or specs.get("manufacturer") or brand
        model_number = (
            specs.get("Model Number")
            or specs.get("Model Name")
            or specs.get("model")
        )
        weight = specs.get("Weight") or specs.get("Product Weight") or specs.get("weight")
        dimensions = specs.get("Dimensions") or specs.get("dimensions")

        return ProductItem(
            marketplace_slug=MARKETPLACE_SLUG,
            external_id=pog_id,
            url=response.url,
            title=title,
            brand=brand,
            price=price,
            mrp=mrp,
            images=images,
            rating=rating,
            review_count=review_count,
            specs=specs,
            seller_name=seller_name or "Snapdeal",
            seller_rating=seller_rating,
            in_stock=in_stock,
            fulfilled_by="Snapdeal",
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
    # Image extraction
    # ------------------------------------------------------------------

    def _extract_images(self, response) -> list[str]:
        """Extract product images from various sources, prefer SDN CDN."""
        images: list[str] = []
        seen: set[str] = set()

        def _add(url: str) -> None:
            if not url or url.startswith("data:"):
                return
            # Clean resize params for full-size images
            clean = url.split("?")[0]
            if clean.startswith("//"):
                clean = "https:" + clean
            if clean not in seen:
                seen.add(clean)
                images.append(clean)

        # itemprop="image" — most reliable
        for img in response.css("[itemprop='image']::attr(src)").getall():
            _add(img)
        for img in response.css("[itemprop='image']::attr(content)").getall():
            _add(img)

        # Lazy-loaded thumbnail images (Snapdeal CDN: i1-i4.sdlcdn.com)
        for img in response.css(
            "img[data-src]::attr(data-src), "
            "img.lazy-load::attr(data-src)"
        ).getall():
            if "sdlcdn.com" in img:
                _add(img)

        # Product image gallery
        for img in response.css(
            ".thumbnail-list img::attr(src), "
            ".pdp-image img::attr(src), "
            ".pdpImage img::attr(src)"
        ).getall():
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
        """Extract product specifications from spec table rows."""
        specs: dict[str, str] = {}

        # Primary: specification rows (table or div based)
        for row in response.css(
            ".specification-row, "
            ".detailssubbox tr, "
            ".spec-row, "
            ".spec-body .spec-row"
        ):
            label = row.css(
                ".spec-label::text, "
                "td:first-child::text, "
                ".spec-title::text"
            ).get()
            value = row.css(
                ".spec-value::text, "
                "td:last-child::text, "
                ".spec-desc::text"
            ).get()
            if label and value and label.strip() and value.strip():
                specs[label.strip()] = value.strip()

        # Fallback: key-value pairs from detail sections
        for row in response.css(".product-spec-value"):
            label = row.css("::attr(title)").get()
            value = row.css("::text").get()
            if label and value and label.strip() and value.strip():
                specs[label.strip()] = value.strip()

        return specs

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
