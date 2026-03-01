"""Flipkart spider — scrapes product listings, detail pages, prices, and offers.

Two-phase architecture:
  Phase 1 — Listing pages (/search?q=...) use Playwright (React-rendered).
            Includes block detection (403, 429, Access Denied).
  Phase 2 — Product detail pages try PLAIN HTTP first.
            Flipkart serves JSON-LD structured data in the initial HTML.
            Only falls back to Playwright if JSON-LD is missing/incomplete.

Strategy:
  1. JSON-LD structured data (``<script type="application/ld+json">``) is the
     primary source for title, price, brand, rating, images, availability, and
     seller.  Flipkart reliably includes schema.org Product markup.
  2. CSS/XPath fallbacks extract the same data when JSON-LD is absent.
  3. Specs, highlights, offers, MRP, and fulfilment info are CSS/XPath only.

Sprint 2, Week 5.
"""
import json
import os
import random
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

import scrapy
from scrapy_playwright.page import PageMethod

from apps.scraping.items import ProductItem
from .base_spider import BaseWhydudSpider

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FPID_RE = re.compile(r"/p/(itm[a-zA-Z0-9]+)")
PRICE_RE = re.compile(r"[\d,.]+")
RATING_NUM_RE = re.compile(r"([\d.]+)")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review)", re.IGNORECASE)

MARKETPLACE_SLUG = "flipkart"

# ---------------------------------------------------------------------------
# Flipkart search keyword → Whydud category slug mapping
# ---------------------------------------------------------------------------

KEYWORD_CATEGORY_MAP: dict[str, str] = {
    # Smartphones & Accessories
    "smartphones": "smartphones",
    "phone cases covers": "smartphones",
    "screen protectors": "smartphones",
    "power banks": "smartphones",
    "mobile chargers": "smartphones",
    "mobile holders stands": "smartphones",
    # Computers & Peripherals
    "laptops": "laptops",
    "tablets": "tablets",
    "monitors": "laptops",
    "computer keyboards": "laptops",
    "computer mouse": "laptops",
    "printers": "laptops",
    "routers": "laptops",
    "external hard drives": "laptops",
    "pen drives": "laptops",
    "graphics cards": "laptops",
    "webcams": "cameras",
    # Audio
    "headphones": "audio",
    "earbuds tws": "audio",
    "bluetooth speakers": "audio",
    "soundbars": "audio",
    "microphones": "audio",
    "home theatre systems": "audio",
    # Wearables
    "smartwatches": "smartwatches",
    "fitness bands": "smartwatches",
    # Cameras & Photography
    "cameras": "cameras",
    "camera lenses": "cameras",
    "camera tripods": "cameras",
    "action cameras": "cameras",
    "drones cameras": "cameras",
    # TVs & Entertainment
    "televisions": "televisions",
    "projectors": "televisions",
    "streaming devices": "televisions",
    "tv wall mounts": "televisions",
    # Large Appliances
    "refrigerators": "refrigerators",
    "washing machines": "washing-machines",
    "air conditioners": "air-conditioners",
    "microwave ovens": "appliances",
    "dishwashers": "appliances",
    "water heaters geysers": "appliances",
    "chimneys": "appliances",
    # Small Appliances
    "air purifiers": "appliances",
    "water purifiers": "appliances",
    "vacuum cleaners": "appliances",
    "robot vacuum cleaners": "appliances",
    "mixer grinders": "kitchen-tools",
    "induction cooktops": "kitchen-tools",
    "electric kettles": "kitchen-tools",
    "air fryers": "kitchen-tools",
    "coffee machines": "kitchen-tools",
    "irons steamers": "kitchen-tools",
    "fans": "appliances",
    "room heaters": "appliances",
    "juicer mixer grinder": "kitchen-tools",
    "hand blenders": "kitchen-tools",
    "sandwich makers": "kitchen-tools",
    "toasters": "kitchen-tools",
    "rice cookers": "kitchen-tools",
    "pressure cookers": "kitchen-tools",
    # Personal Care & Grooming
    "trimmers": "grooming",
    "electric shavers": "grooming",
    "hair dryers": "grooming",
    "hair straighteners": "grooming",
    "electric toothbrushes": "grooming",
    "epilators": "grooming",
    # Fitness & Sports
    "treadmills": "fitness",
    "exercise bikes": "fitness",
    "dumbbells weights": "fitness",
    "yoga mats": "fitness",
    "gym equipment": "fitness",
    # Home & Furniture
    "mattresses": "home-kitchen",
    "office chairs": "home-kitchen",
    "study tables": "home-kitchen",
    "beds": "home-kitchen",
    "sofas": "home-kitchen",
    "shoe racks": "home-kitchen",
    "dining tables": "home-kitchen",
    "wardrobes": "home-kitchen",
    "bean bags": "home-kitchen",
    "curtains": "home-kitchen",
    "bedsheets": "home-kitchen",
    # Smart Home & Security
    "smart plugs": "electronics",
    "smart bulbs": "electronics",
    "security cameras": "cameras",
    "smart door locks": "electronics",
    "video doorbells": "electronics",
    "smart speakers": "electronics",
    # Gaming
    "gaming laptops": "laptops",
    "gaming monitors": "laptops",
    "gaming headsets": "audio",
    "gaming controllers": "electronics",
    "gaming chairs": "home-kitchen",
    "gaming consoles": "electronics",
    # Storage & Networking
    "ssd internal": "laptops",
    "memory cards": "laptops",
    "wifi mesh systems": "laptops",
    # Baby & Kids
    "baby strollers": "baby-kids",
    "car seats baby": "baby-kids",
    "baby monitors": "cameras",
    "baby toys": "baby-kids",
    # Car & Bike Accessories
    "dash cameras": "cameras",
    "car chargers": "electronics",
    "car air purifiers": "appliances",
    "tyre inflators": "electronics",
    "car accessories": "electronics",
    "helmet": "automotive",
    # Musical Instruments
    "guitars": "electronics",
    "keyboards pianos": "electronics",
    # Luggage & Bags
    "laptop bags backpacks": "fashion",
    "suitcases trolley": "fashion",
    "handbags": "fashion",
    # Books & Stationery
    "books bestsellers": "books",
    "school bags": "books",
    # Fashion & Accessories
    "sunglasses": "fashion",
    "watches men": "fashion",
    "watches women": "fashion",
    # Kitchen & Dining
    "cookware sets": "kitchen-tools",
    "water bottles": "kitchen-tools",
    "lunch boxes": "kitchen-tools",
    "kitchen storage": "kitchen-tools",
}


# Seed category search URLs — used when no ScraperJob provides URLs.
# Format: (url, max_pages) — controls pagination depth per category.
# Top categories get 30 pages (~480 products), standard get 20 pages (~320 products).

_TOP = 30   # pages for top categories
_STD = 20   # pages for standard categories

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones & Accessories (TOP) ──────────────────────────────────
    ("https://www.flipkart.com/search?q=smartphones&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=phone+cases+covers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=screen+protectors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=power+banks&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=mobile+chargers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=mobile+holders+stands&sort=popularity", _STD),
    # ── Computers & Peripherals (TOP) ────────────────────────────────────
    ("https://www.flipkart.com/search?q=laptops&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=tablets&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=monitors&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=computer+keyboards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=computer+mouse&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=printers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=routers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=external+hard+drives&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=pen+drives&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=graphics+cards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=webcams&sort=popularity", _STD),
    # ── Audio (TOP) ──────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=headphones&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=earbuds+tws&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=bluetooth+speakers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=soundbars&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=microphones&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=home+theatre+systems&sort=popularity", _STD),
    # ── Wearables (TOP) ──────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=smartwatches&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=fitness+bands&sort=popularity", _STD),
    # ── Cameras & Photography ────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=cameras&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=camera+lenses&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=camera+tripods&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=action+cameras&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=drones+cameras&sort=popularity", _STD),
    # ── TVs & Entertainment (TOP) ────────────────────────────────────────
    ("https://www.flipkart.com/search?q=televisions&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=projectors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=streaming+devices&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=tv+wall+mounts&sort=popularity", _STD),
    # ── Large Appliances (TOP) ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=refrigerators&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=washing+machines&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=air+conditioners&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=microwave+ovens&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dishwashers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=water+heaters+geysers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=chimneys&sort=popularity", _STD),
    # ── Small Appliances ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=air+purifiers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=water+purifiers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=vacuum+cleaners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=robot+vacuum+cleaners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=mixer+grinders&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=induction+cooktops&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=electric+kettles&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=air+fryers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=coffee+machines&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=irons+steamers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=fans&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=room+heaters&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=juicer+mixer+grinder&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hand+blenders&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=sandwich+makers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=toasters&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=rice+cookers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=pressure+cookers&sort=popularity", _STD),
    # ── Personal Care & Grooming (TOP) ───────────────────────────────────
    ("https://www.flipkart.com/search?q=trimmers&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=electric+shavers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hair+dryers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=hair+straighteners&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=electric+toothbrushes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=epilators&sort=popularity", _STD),
    # ── Fitness & Sports ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=treadmills&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=exercise+bikes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dumbbells+weights&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=yoga+mats&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gym+equipment&sort=popularity", _STD),
    # ── Home & Furniture (TOP) ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=mattresses&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=office+chairs&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=study+tables&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=beds&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=sofas&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=shoe+racks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=dining+tables&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=wardrobes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=bean+bags&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=curtains&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=bedsheets&sort=popularity", _STD),
    # ── Smart Home & Security (TOP) ──────────────────────────────────────
    ("https://www.flipkart.com/search?q=smart+plugs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=smart+bulbs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=security+cameras&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=smart+door+locks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=video+doorbells&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=smart+speakers&sort=popularity", _STD),
    # ── Gaming (TOP) ─────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=gaming+laptops&sort=popularity", _TOP),
    ("https://www.flipkart.com/search?q=gaming+monitors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+headsets&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+controllers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+chairs&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=gaming+consoles&sort=popularity", _STD),
    # ── Storage & Networking ─────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=ssd+internal&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=memory+cards&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=wifi+mesh+systems&sort=popularity", _STD),
    # ── Baby & Kids ──────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=baby+strollers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+seats+baby&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=baby+monitors&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=baby+toys&sort=popularity", _STD),
    # ── Car & Bike Accessories ───────────────────────────────────────────
    ("https://www.flipkart.com/search?q=dash+cameras&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+chargers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+air+purifiers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=tyre+inflators&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=car+accessories&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=helmet&sort=popularity", _STD),
    # ── Musical Instruments ──────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=guitars&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=keyboards+pianos&sort=popularity", _STD),
    # ── Luggage & Bags ───────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=laptop+bags+backpacks&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=suitcases+trolley&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=handbags&sort=popularity", _STD),
    # ── Books ────────────────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=books+bestsellers&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=school+bags&sort=popularity", _STD),
    # ── Fashion & Accessories ────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=sunglasses&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=watches+men&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=watches+women&sort=popularity", _STD),
    # ── Kitchen & Dining ─────────────────────────────────────────────────
    ("https://www.flipkart.com/search?q=cookware+sets&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=water+bottles&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=lunch+boxes&sort=popularity", _STD),
    ("https://www.flipkart.com/search?q=kitchen+storage&sort=popularity", _STD),
]

MAX_LISTING_PAGES = 5


class FlipkartSpider(BaseWhydudSpider):
    """Scrapes Flipkart with a two-phase approach.

    Phase 1: Listing pages via Playwright (React-rendered, lazy-loaded cards).
             Includes block detection for 403/429/Access Denied.
    Phase 2: Product detail pages try plain HTTP first (JSON-LD is in raw HTML).
             Falls back to Playwright only when JSON-LD data is incomplete.

    Spider arguments (passed via ``-a``):
      job_id        — UUID of a ScraperJob row.
      category_urls — comma-separated override URLs.
      max_pages     — override MAX_LISTING_PAGES (default 5).
      save_html     — "1" to save raw HTML for debugging.
    """

    name = "flipkart"
    allowed_domains = ["flipkart.com", "www.flipkart.com"]

    # Quick mode: only use first N categories when --max-pages <= 3
    QUICK_MODE_CATEGORIES = 10

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 10,
        "CONCURRENT_REQUESTS": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 1,
        # Flipkart serves valid page content with 403 status codes (anti-bot
        # challenge pages that still render product data via JS). Allow the
        # spider to process these responses instead of discarding them.
        "HTTPERROR_ALLOWED_CODES": [403],
    }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(
        self,
        job_id: str | None = None,
        category_urls: str | None = None,
        max_pages: str | None = None,
        save_html: str = "0",
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
        # --max-pages CLI arg acts as a global override for ALL categories.
        # When not set, per-category limits from SEED_CATEGORY_URLS are used.
        self._max_pages_override: int | None = int(max_pages) if max_pages else None
        self._save_html = save_html == "1"
        self._pages_followed: dict[str, int] = {}
        self._max_pages_map: dict[str, int] = {}  # base_url → per-category limit

        # Proxy mode: rotating proxies get fewer block retries (new IP each time)
        self._is_rotating = (
            os.environ.get("SCRAPING_PROXY_TYPE", "static").lower() == "rotating"
        )

        # Scrape stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._product_pages_plain_http: int = 0
        self._product_pages_playwright: int = 0
        self._blocked_count: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Flipkart spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"plain_http={self._product_pages_plain_http}, "
            f"playwright={self._product_pages_playwright}, "
            f"blocked={self._blocked_count}, "
            f"failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests — Phase 1: Playwright for listings
    # ------------------------------------------------------------------

    async def _apply_stealth(self, page, request):
        """Apply playwright-stealth scripts to a page before navigation."""
        try:
            await self.STEALTH.apply_stealth_async(page)
            # Increase timeouts for proxy connections (DataImpulse adds latency)
            page.set_default_navigation_timeout(60000)  # 60s instead of 30s
            page.set_default_timeout(45000)  # 45s for other operations
        except Exception as e:
            self.logger.warning(f"Stealth setup issue: {e}")

    def start_requests(self):
        """Emit Playwright requests for all category listing pages.

        Flipkart listing pages are React-rendered — Playwright is required.
        Categories are shuffled to distribute load.
        """
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = re.sub(r"[&?]page=\d+", "", url)
            self._max_pages_map[base] = max_pg
            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            # Phase 1: Playwright for listing pages (React-rendered)
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "networkidle"),
                    ],
                    "category_slug": self._resolve_category_from_url(url),
                },
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (Playwright)")

    def _load_urls(self) -> list[tuple[str, int]]:
        """Resolve the list of (url, max_pages) pairs to crawl.

        Priority: CLI ``category_urls`` > ScraperJob > seed categories.
        The ``--max-pages`` CLI arg overrides per-category limits globally.
        Quick mode: when --max-pages <= 3, only use top N categories.
        """
        fallback = self._max_pages_override or MAX_LISTING_PAGES

        # 1. Explicit CLI override — flat URLs, use global limit
        if self._category_urls:
            return [(u, fallback) for u in self._category_urls]

        # 2. ScraperJob (from DB)
        if self.job_id:
            try:
                from apps.scraping.models import ScraperJob

                job = ScraperJob.objects.get(id=self.job_id)
                self.logger.info(
                    f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}"
                )
            except Exception as exc:
                self.logger.warning(f"Could not load ScraperJob {self.job_id}: {exc}")

        # 3. Fallback to seed categories
        if self._max_pages_override is not None:
            # Quick mode: take top N categories only for small runs
            if self._max_pages_override <= 3:
                self.logger.info(
                    f"Quick mode: using first {self.QUICK_MODE_CATEGORIES} categories "
                    f"(max_pages={self._max_pages_override})"
                )
                return [
                    (url, self._max_pages_override)
                    for url, _ in SEED_CATEGORY_URLS[:self.QUICK_MODE_CATEGORIES]
                ]
            # CLI --max-pages overrides every per-category limit
            return [(url, self._max_pages_override) for url, _ in SEED_CATEGORY_URLS]
        return list(SEED_CATEGORY_URLS)

    # ------------------------------------------------------------------
    # Phase 1: Listing page (search results / category pages)
    # ------------------------------------------------------------------

    def parse_listing_page(self, response):
        """Extract product links from a Flipkart search/category page.

        Includes block detection for 403, 429, and Access Denied responses.
        """
        self._listing_pages_scraped += 1
        block_retries = response.meta.get("block_retries", 0)

        # Block detection: 403/429 status codes
        if response.status in (403, 429):
            # Check if it's a real block vs Flipkart's normal 403-with-content
            if not response.css('a[href*="/p/itm"]'):
                self._blocked_count += 1

                # With rotating proxies, retry once (next request gets new IP)
                max_retries = 1 if self._is_rotating else 0
                if block_retries < max_retries:
                    self.logger.info(
                        f"Flipkart blocked listing HTTP {response.status} — "
                        f"retry {block_retries + 1}/{max_retries}: {response.url}"
                    )
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
                            ],
                            "category_slug": response.meta.get("category_slug"),
                            "block_retries": block_retries + 1,
                        },
                        dont_filter=True,
                        priority=-1,
                    )
                    return

                self.logger.warning(
                    f"Flipkart blocked listing page: HTTP {response.status} on {response.url}"
                )
                self.items_failed += 1
                return

        # Flipkart product links always contain /p/itm
        product_links = response.css('a[href*="/p/itm"]::attr(href)').getall()
        # Deduplicate while preserving order
        seen: set[str] = set()
        unique_links: list[str] = []
        for link in product_links:
            full = response.urljoin(link)
            # Normalise — strip query params and ref tags for dedup
            canon = full.split("?")[0]
            if canon not in seen:
                seen.add(canon)
                unique_links.append(full)

        if not unique_links:
            # Check for Access Denied block
            if "Access Denied" in response.text[:1000]:
                self._blocked_count += 1

                # With rotating proxies, retry once
                max_retries = 1 if self._is_rotating else 0
                if block_retries < max_retries:
                    self.logger.info(
                        f"Flipkart Access Denied — retry {block_retries + 1}/{max_retries}: {response.url}"
                    )
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
                            ],
                            "category_slug": response.meta.get("category_slug"),
                            "block_retries": block_retries + 1,
                        },
                        dont_filter=True,
                        priority=-1,
                    )
                    return

                self.logger.warning(f"Flipkart Access Denied on {response.url}")
                self.items_failed += 1
                return
            self.logger.warning(f"No product links found on {response.url}")
            return

        self.logger.info(f"Found {len(unique_links)} products on {response.url}")

        category_slug = response.meta.get("category_slug") or self._resolve_category_from_url(response.url)

        for link in unique_links:
            # Phase 2: Try plain HTTP first for product pages
            # No proxy_session — let middleware round-robin per request
            yield scrapy.Request(
                link,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={"category_slug": category_slug},
            )

        # Pagination — follow "Next" link up to per-category max_pages
        base_url = re.sub(r"[&?]page=\d+", "", response.url)
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)
        if pages_so_far < max_for_category:
            next_link = self._find_next_page(response)
            if next_link:
                self._pages_followed[base_url] = pages_so_far + 1
                # Stay in Playwright for next listing page
                yield scrapy.Request(
                    response.urljoin(next_link),
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "playwright_page_methods": [
                            PageMethod("wait_for_load_state", "networkidle"),
                        ],
                        "category_slug": category_slug,
                    },
                )

    @staticmethod
    def _find_next_page(response) -> str | None:
        """Locate the "Next" pagination link."""
        # Flipkart uses <nav> with numbered + next links
        for a in response.css("nav a"):
            text = a.css("::text").get("").strip().lower()
            if text == "next":
                return a.attrib.get("href")
        # Fallback: look for an anchor whose span contains "Next"
        nav_link = response.xpath(
            '//a[.//span[contains(text(),"Next")]]/@href'
        ).get()
        return nav_link

    # ------------------------------------------------------------------
    # Phase 2: Product detail page (plain HTTP first → Playwright fallback)
    # ------------------------------------------------------------------

    def parse_product_page(self, response):
        """Extract product data — tries plain HTTP + JSON-LD first.

        If JSON-LD has title + price → sufficient, no Playwright needed.
        If incomplete and this was plain HTTP → retry with Playwright.
        If this was already Playwright → extract whatever we can.
        """
        self._product_pages_scraped += 1

        # Check middleware's CAPTCHA flag first (rotating proxy already detected it)
        if response.meta.get("_rotating_proxy_captcha"):
            self._captcha_count = getattr(self, "_captcha_count", 0) + 1
            self.items_failed += 1
            self.logger.debug(
                f"CAPTCHA flagged by proxy middleware — skipping {response.url[:60]}"
            )
            return

        is_playwright = response.meta.get("playwright", False)

        if is_playwright:
            self._product_pages_playwright += 1
        else:
            self._product_pages_plain_http += 1

        # Block detection
        if response.status in (403, 429) and not is_playwright:
            # Plain HTTP got blocked — promote to Playwright
            self.logger.info(f"HTTP {response.status} on product page — promoting to Playwright: {response.url}")
            yield scrapy.Request(
                response.url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                    "category_slug": response.meta.get("category_slug"),
                },
                dont_filter=True,
            )
            return

        fpid = self._extract_fpid(response)
        if not fpid:
            self.logger.warning(f"Could not extract FPID from {response.url}")
            self.items_failed += 1
            return

        # Parse JSON-LD once — used by many extractors
        ld_json = self._parse_json_ld(response)

        # Check if we have enough data from plain HTML + JSON-LD
        has_title = bool(
            (ld_json and ld_json.get("name"))
            or response.css("span.VU-ZEz::text").get()
            or response.css("h1 span::text").get()
        )
        has_price = bool(
            (ld_json and ld_json.get("offers"))
            or response.css("div._30jeq3::text").get()
            or response.css("div.Nx9bqj::text").get()
        )

        if has_title and has_price:
            # Success — extract from HTML + JSON-LD
            yield from self._build_item(response, fpid, ld_json)
            return

        # Insufficient data — if plain HTTP, retry with Playwright
        if not is_playwright:
            self.logger.info(
                f"Incomplete data for FPID {fpid} (title={has_title}, price={has_price}) "
                f"— promoting to Playwright"
            )
            yield scrapy.Request(
                response.url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                    ],
                    "category_slug": response.meta.get("category_slug"),
                },
                dont_filter=True,
            )
            return

        # Already Playwright — extract whatever we can
        yield from self._build_item(response, fpid, ld_json)

    def _build_item(self, response, fpid: str, ld_json: dict | None):
        """Build and yield a ProductItem from HTML + JSON-LD data."""
        title = self._extract_title(response, ld_json)
        if not title:
            self.logger.warning(f"No title found for FPID {fpid}")
            self.items_failed += 1
            return

        raw_html_path = None
        if self._save_html:
            raw_html_path = self._save_raw_html(response, fpid)

        item = ProductItem()
        item["marketplace_slug"] = MARKETPLACE_SLUG
        item["external_id"] = fpid
        item["url"] = self._canonical_url(response.url, fpid)
        item["title"] = title
        item["brand"] = self._extract_brand(response, ld_json)
        item["price"] = self._extract_price(response, ld_json)
        item["mrp"] = self._extract_mrp(response)
        item["images"] = self._extract_images(response, ld_json)
        item["rating"] = self._extract_rating(response, ld_json)
        item["review_count"] = self._extract_review_count(response, ld_json)
        item["specs"] = self._extract_specs(response)
        item["seller_name"] = self._extract_seller(response, ld_json)
        item["seller_rating"] = self._extract_seller_rating(response)
        item["in_stock"] = self._extract_availability(response, ld_json)
        item["fulfilled_by"] = self._extract_fulfilled_by(response)
        item["category_slug"] = response.meta.get("category_slug")
        item["about_bullets"] = self._extract_highlights(response)
        item["offer_details"] = self._extract_offers(response)
        item["raw_html_path"] = raw_html_path

        # Extended fields — comprehensive product info
        item["description"] = self._extract_description(response, ld_json)
        item["warranty"] = self._extract_warranty(response)
        item["delivery_info"] = self._extract_delivery_info(response)
        item["return_policy"] = self._extract_return_policy(response)
        item["breadcrumbs"] = self._extract_breadcrumbs(response)
        item["variant_options"] = self._extract_variants(response)
        specs = item["specs"]
        item["country_of_origin"] = self._extract_from_specs(specs, ["Country of Origin", "country of origin", "Country Of Origin"])
        item["manufacturer"] = self._extract_from_specs(specs, ["Manufacturer", "manufacturer"])
        item["model_number"] = self._extract_from_specs(specs, ["Model Number", "Model Name", "model number"])
        item["weight"] = self._extract_from_specs(specs, ["Weight", "Net Weight", "weight", "Product Weight"])
        item["dimensions"] = self._extract_from_specs(specs, ["Dimensions", "Product Dimensions", "dimensions"])

        self.items_scraped += 1
        self._products_extracted += 1
        yield item

    # ------------------------------------------------------------------
    # JSON-LD extraction
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_json_ld(response) -> dict | None:
        """Extract the first schema.org Product JSON-LD block from the page."""
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
            except (json.JSONDecodeError, ValueError):
                continue

            # Might be a single object or an array
            if isinstance(data, list):
                for obj in data:
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
            elif isinstance(data, dict):
                if data.get("@type") == "Product":
                    return data
                # Sometimes nested inside @graph
                for obj in data.get("@graph", []):
                    if isinstance(obj, dict) and obj.get("@type") == "Product":
                        return obj
        return None

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_fpid(response) -> str | None:
        """Extract Flipkart Product ID (FPID) from URL.

        Handles URL patterns:
          /product-name/p/itmXXXX             (standard)
          /product-name/p/itmXXXX?pid=XXXX    (with tracking)
          /dl/product-name/p/itmXXXX          (deep link)
        """
        match = FPID_RE.search(response.url)
        if match:
            return match.group(1)
        # Fallback: look for pid parameter in URL query
        if "pid=" in response.url:
            pid = response.url.split("pid=")[-1].split("&")[0]
            if pid:
                return pid
        return None

    @staticmethod
    def _extract_title(response, ld_json: dict | None) -> str | None:
        """Extract product title."""
        # JSON-LD
        if ld_json and ld_json.get("name"):
            return ld_json["name"].strip()
        # CSS fallbacks — Flipkart class names change, try multiple patterns
        for sel in [
            "span.VU-ZEz::text",       # Common product title class
            "h1._6EBuvT span::text",    # Alternative wrapper
            "h1 span.B_NuCI::text",     # Another variant
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        # XPath: first h1 or large span in the product info column
        title = response.xpath(
            '//div[contains(@class,"aMaAEs") or contains(@class,"hGSR34")]'
            '//span[string-length(text()) > 10]/text()'
        ).get()
        return title.strip() if title else None

    @staticmethod
    def _extract_brand(response, ld_json: dict | None) -> str | None:
        """Extract brand name."""
        # JSON-LD
        if ld_json:
            brand_obj = ld_json.get("brand")
            if isinstance(brand_obj, dict) and brand_obj.get("name"):
                return brand_obj["name"].strip()
            if isinstance(brand_obj, str) and brand_obj.strip():
                return brand_obj.strip()
        # CSS: breadcrumb often contains brand
        breadcrumbs = response.css("div._1MR4o5 a::text, div._2whKao a::text").getall()
        if len(breadcrumbs) >= 3:
            # Breadcrumb pattern: Home > Category > Brand > ...
            return breadcrumbs[2].strip()
        # XPath: Specs table sometimes has "Brand"
        brand = response.xpath(
            '//td[text()="Brand" or text()="brand"]/following-sibling::td//text()'
        ).get()
        return brand.strip() if brand else None

    def _extract_price(self, response, ld_json: dict | None) -> Decimal | None:
        """Extract current sale price in paisa."""
        # JSON-LD offers
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                price = self._json_ld_price(offers)
                if price is not None:
                    return price
            elif isinstance(offers, list):
                for offer in offers:
                    price = self._json_ld_price(offer)
                    if price is not None:
                        return price

        # CSS fallbacks
        for sel in [
            "div._30jeq3::text",         # Common sale price class
            "div._16Jk6d::text",          # Alternative
            "div.Nx9bqj::text",           # Newer variant
            "div.hl05eU div.Nx9bqj::text",
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        # XPath: look for the first ₹ price near the buy button area
        price_text = response.xpath(
            '//div[contains(@class,"CEmi") or contains(@class,"_30jeq")]//text()'
        ).get()
        return self._parse_price_text(price_text)

    def _extract_mrp(self, response) -> Decimal | None:
        """Extract MRP (strike-through price) in paisa.

        JSON-LD only contains the sale price, so MRP is always from CSS.
        """
        for sel in [
            "div._3I9_wc::text",          # Common MRP class (strike-through)
            "div._2p6lqe::text",           # Alternative
            "div.yRaY8j::text",            # Newer variant
        ]:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price

        # XPath: strike-through or "M.R.P" text
        mrp_text = response.xpath(
            '//span[contains(@class,"_2p6lq") or contains(@style,"line-through")]//text()'
        ).get()
        return self._parse_price_text(mrp_text)

    def _extract_images(self, response, ld_json: dict | None) -> list[str]:
        """Extract all product image URLs (high resolution)."""
        images: list[str] = []

        # JSON-LD images
        if ld_json:
            img = ld_json.get("image")
            if isinstance(img, str) and img:
                images.append(self._high_res_image(img))
            elif isinstance(img, list):
                for i in img:
                    if isinstance(i, str) and i:
                        images.append(self._high_res_image(i))

        # CSS: image gallery thumbnails → upgrade to full size
        for img_url in response.css(
            'div._3kidJX img::attr(src), '
            'ul._1-n69S li img::attr(src), '
            'div._2E1FGS img::attr(src), '
            'div._1BweB8 img::attr(src)'
        ).getall():
            if "placeholder" in img_url:
                continue
            full = self._high_res_image(img_url)
            if full not in images:
                images.append(full)

        # Fallback: any large product image on the page
        if not images:
            for img_url in response.css('img[src*="rukminim"]::attr(src)').getall():
                full = self._high_res_image(img_url)
                if full not in images:
                    images.append(full)

        return images[:10]

    @staticmethod
    def _extract_rating(response, ld_json: dict | None) -> Decimal | None:
        """Extract average star rating (0-5)."""
        # JSON-LD
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                val = agg.get("ratingValue")
                if val is not None:
                    try:
                        return Decimal(str(val))
                    except InvalidOperation:
                        pass

        # CSS fallbacks
        for sel in [
            "div._3LWZlK::text",       # Common rating badge
            "span._1lRcqv::text",       # Alternative
            "div.XQDdHH::text",         # Newer variant
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    @staticmethod
    def _extract_review_count(response, ld_json: dict | None) -> int | None:
        """Extract total number of ratings/reviews."""
        # JSON-LD
        if ld_json:
            agg = ld_json.get("aggregateRating")
            if isinstance(agg, dict):
                for key in ("reviewCount", "ratingCount"):
                    val = agg.get(key)
                    if val is not None:
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            pass

        # CSS: rating/review count text (e.g., "1,234 Ratings & 567 Reviews")
        for sel in [
            "span._2_R_DZ::text",
            "span._13vcW::text",
            'div[class*="row"] span._2_R_DZ span::text',
        ]:
            for text in response.css(sel).getall():
                match = REVIEW_COUNT_RE.search(text)
                if match:
                    return int(match.group(1).replace(",", ""))

        # XPath fallback
        count_text = response.xpath(
            '//*[contains(text(),"Rating") and contains(text(),"Review")]//text()'
        ).get()
        if count_text:
            match = REVIEW_COUNT_RE.search(count_text)
            if match:
                return int(match.group(1).replace(",", ""))
        return None

    @staticmethod
    def _extract_seller(response, ld_json: dict | None) -> str | None:
        """Extract seller name."""
        # JSON-LD offers.seller
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                seller = offers.get("seller")
                if isinstance(seller, dict) and seller.get("name"):
                    return seller["name"].strip()
            elif isinstance(offers, list):
                for offer in offers:
                    seller = offer.get("seller")
                    if isinstance(seller, dict) and seller.get("name"):
                        return seller["name"].strip()

        # CSS: seller info section
        for sel in [
            "#sellerName span span::text",
            "div._3enH3G span span::text",
            'div[id="sellerName"] a span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()

        return None

    @staticmethod
    def _extract_seller_rating(response) -> Decimal | None:
        """Extract seller rating (shown next to seller name)."""
        for sel in [
            "#sellerName div._3LWZlK::text",
            'div._3enH3G div._3LWZlK::text',
        ]:
            text = response.css(sel).get()
            if text:
                match = RATING_NUM_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    @staticmethod
    def _extract_availability(response, ld_json: dict | None) -> bool:
        """Determine if product is in stock."""
        # JSON-LD
        if ld_json:
            offers = ld_json.get("offers")
            if isinstance(offers, dict):
                avail = offers.get("availability", "")
                if "InStock" in avail:
                    return True
                if "OutOfStock" in avail:
                    return False
            elif isinstance(offers, list):
                for offer in offers:
                    avail = offer.get("availability", "")
                    if "InStock" in avail:
                        return True

        # CSS: check for "Coming Soon" or "Sold Out" or "Currently Unavailable"
        page_text = " ".join(response.css("div._16FRp0::text, div._1dVbu9::text").getall()).lower()
        if "sold out" in page_text or "coming soon" in page_text or "currently unavailable" in page_text:
            return False

        # If there's an "Add to Cart" or "Buy Now" button, assume in stock
        buy_btn = response.css(
            'button._2KpZ6l::text, button.QqFHMw::text, '
            'button[class*="BUY"]::text, button[class*="add-to-cart"]::text'
        ).getall()
        for btn_text in buy_btn:
            lower = btn_text.strip().lower()
            if "buy now" in lower or "add to cart" in lower:
                return True

        # Default: if we found a price, assume in stock
        return bool(response.css("div._30jeq3, div.Nx9bqj"))

    @staticmethod
    def _extract_fulfilled_by(response) -> str | None:
        """Extract fulfilment info — Flipkart Assured or seller-fulfilled."""
        # Flipkart Assured badge
        assured = response.css(
            'img[src*="fa_62673a"]::attr(src), '  # Assured icon URL pattern
            'img[alt*="Assured"]::attr(alt), '
            'img[src*="fk-advantage"]::attr(src)'
        ).get()
        if assured:
            return "Flipkart"

        # XPath: look for "Flipkart Assured" text
        assured_text = response.xpath(
            '//*[contains(text(),"Flipkart Assured") or contains(text(),"F-Assured")]'
        ).get()
        if assured_text:
            return "Flipkart"

        return None

    @staticmethod
    def _extract_specs(response) -> dict[str, str]:
        """Extract technical specifications as key-value pairs.

        Flipkart organises specs in tables under a "Specifications" heading,
        grouped by category (General, Display, Performance, etc.).
        """
        specs: dict[str, str] = {}

        # Primary: specification tables (multiple grouped tables)
        for row in response.css("div._14cfVK tr, table._14cfVK tr"):
            key = row.css("td:first-child::text").get("").strip()
            val = row.css("td:last-child li::text, td:last-child::text").get("").strip()
            if key and val and key != val:
                specs[key] = val

        # Alternative class names
        if not specs:
            for row in response.css("div._3k-BhJ tr, table.G4BRas tr, table._3npaEj tr"):
                key = row.css("td:first-child::text").get("").strip()
                val = row.css("td:last-child::text").get("").strip()
                if key and val and key != val:
                    specs[key] = val

        # XPath fallback: look for the "Specifications" section
        if not specs:
            spec_rows = response.xpath(
                '//div[.//text()="Specifications" or .//text()="SPECIFICATIONS"]'
                '//following-sibling::div//table//tr'
            )
            for row in spec_rows:
                cells = row.xpath(".//td//text()").getall()
                cells = [c.strip() for c in cells if c.strip()]
                if len(cells) >= 2:
                    specs[cells[0]] = cells[-1]

        return specs

    @staticmethod
    def _extract_highlights(response) -> list[str]:
        """Extract product highlights / key features bullet points."""
        bullets: list[str] = []

        # Primary selectors
        for sel in [
            "div._2418kt li::text",
            "div.xFVion li::text",
            "div._3Rrcbo li::text",
        ]:
            items = response.css(sel).getall()
            if items:
                bullets = [b.strip() for b in items if b.strip()]
                break

        # XPath fallback: section headed "Highlights"
        if not bullets:
            items = response.xpath(
                '//div[.//text()="Highlights" or .//text()="HIGHLIGHTS"]'
                '//following-sibling::div[1]//li//text()'
            ).getall()
            bullets = [b.strip() for b in items if b.strip()]

        return bullets

    @staticmethod
    def _extract_offers(response) -> list[dict]:
        """Extract bank offers, exchange offers, and EMI details."""
        offers: list[dict] = []

        # Offer cards on Flipkart — usually in a specific section
        offer_selectors = [
            "div._3Ht4Hy li",      # Offer list items
            "div.DaXhCo li",       # Alternative
            "div._16eBzU li",      # Another variant
        ]

        offer_elements = []
        for sel in offer_selectors:
            offer_elements = response.css(sel)
            if offer_elements:
                break

        for elem in offer_elements:
            text_parts = elem.css("::text").getall()
            offer_text = " ".join(t.strip() for t in text_parts if t.strip())
            if not offer_text or len(offer_text) < 10:
                continue

            offer: dict = {"text": offer_text[:500]}
            lower = offer_text.lower()

            if "cashback" in lower:
                offer["type"] = "cashback"
            elif "no cost emi" in lower or "emi" in lower:
                offer["type"] = "emi"
            elif "exchange" in lower:
                offer["type"] = "exchange"
            elif "coupon" in lower:
                offer["type"] = "coupon"
            elif "bank" in lower or "card" in lower:
                offer["type"] = "bank_offer"
            elif "partner" in lower:
                offer["type"] = "partner_offer"
            else:
                offer["type"] = "other"

            offers.append(offer)

        # XPath fallback: look for "Available offers" section
        if not offers:
            offer_items = response.xpath(
                '//div[.//text()="Available offers" or .//text()="Available Offers"]'
                '//following-sibling::div[1]//li'
            )
            for li in offer_items:
                text_parts = li.xpath(".//text()").getall()
                offer_text = " ".join(t.strip() for t in text_parts if t.strip())
                if offer_text and len(offer_text) >= 10:
                    lower = offer_text.lower()
                    offer_type = "other"
                    if "cashback" in lower:
                        offer_type = "cashback"
                    elif "emi" in lower:
                        offer_type = "emi"
                    elif "exchange" in lower:
                        offer_type = "exchange"
                    elif "bank" in lower or "card" in lower:
                        offer_type = "bank_offer"
                    offers.append({"text": offer_text[:500], "type": offer_type})

        return offers[:10]

    # ------------------------------------------------------------------
    # Extended field extraction (description, warranty, delivery, etc.)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_description(response, ld_json: dict | None) -> str | None:
        """Extract product description from JSON-LD or page content."""
        # JSON-LD description
        if ld_json and ld_json.get("description"):
            return ld_json["description"].strip()[:5000]

        # Flipkart product description section
        desc_parts = response.css("div._1mXcCf p::text, div._1mXcCf::text").getall()
        if desc_parts:
            return " ".join(t.strip() for t in desc_parts if t.strip())[:5000]

        # Fallback: look for "Description" section
        desc = response.xpath(
            '//div[.//text()="Description" or .//text()="DESCRIPTION"]'
            '//following-sibling::div[1]//text()'
        ).getall()
        if desc:
            return " ".join(t.strip() for t in desc if t.strip())[:5000]

        return None

    @staticmethod
    def _extract_warranty(response) -> str | None:
        """Extract warranty information from specs or dedicated section."""
        # Check specs table for warranty
        for row in response.css("div._14cfVK tr, table._14cfVK tr, div._3k-BhJ tr"):
            key = row.css("td:first-child::text").get("").strip().lower()
            if "warranty" in key:
                return row.css("td:last-child::text, td:last-child li::text").get("").strip()

        # XPath fallback for "Warranty" section
        warranty = response.xpath(
            '//td[contains(translate(text(),"WARRANTY","warranty"),"warranty")]'
            '/following-sibling::td//text()'
        ).get()
        return warranty.strip() if warranty else None

    @staticmethod
    def _extract_delivery_info(response) -> str | None:
        """Extract delivery estimate."""
        # Flipkart delivery info near pincode section
        for sel in [
            "div._3XINqE::text",
            "div._1TPvmH span::text",
            "div._2H87wv span::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip() and "deliver" in text.lower():
                return text.strip()
        return None

    @staticmethod
    def _extract_return_policy(response) -> str | None:
        """Extract return policy text."""
        # Flipkart return policy is often in the offers/services section
        for sel in [
            "div._3n2dkM::text",
            "div._2TnXLR span::text",
        ]:
            text = response.css(sel).get()
            if text and text.strip() and "return" in text.lower():
                return text.strip()

        # XPath for return policy section
        ret = response.xpath(
            '//*[contains(text(),"Return Policy") or contains(text(),"day replacement")]//text()'
        ).get()
        return ret.strip() if ret else None

    @staticmethod
    def _extract_breadcrumbs(response) -> list[str]:
        """Extract navigation breadcrumb trail."""
        crumbs = response.css("div._1MR4o5 a::text, div._2whKao a::text").getall()
        if crumbs:
            return [c.strip() for c in crumbs if c.strip()]
        # XPath fallback
        crumbs = response.xpath('//div[contains(@class,"breadcrumb")]//a//text()').getall()
        return [c.strip() for c in crumbs if c.strip()]

    @staticmethod
    def _extract_variants(response) -> list[dict]:
        """Extract available variant options (color, RAM, storage, etc.)."""
        variants: list[dict] = []

        # Flipkart variant selectors (thumbnail swatches and text options)
        for swatch in response.css("div._3V2wfe a, div._1fGeJ5 a, a._2GcJMG"):
            label = swatch.css("::attr(title)").get() or swatch.css("::text").get()
            href = swatch.css("::attr(href)").get()
            if label and label.strip():
                variant = {"value": label.strip()}
                if href and "/p/" in href:
                    variant["url"] = response.urljoin(href)
                variants.append(variant)

        # ID-based variant buttons (RAM/Storage selection)
        for btn in response.css("div._3V2wfe div, li._1fGeJ5"):
            text = btn.css("a::text").get() or btn.css("::text").get()
            if text and text.strip():
                variants.append({"value": text.strip()})

        return variants[:30]

    @staticmethod
    def _extract_from_specs(specs: dict, keys: list[str]) -> str | None:
        """Extract a specific value from specs dict by trying multiple key names."""
        if not specs:
            return None
        for key in keys:
            if key in specs:
                return specs[key]
            for spec_key, spec_val in specs.items():
                if spec_key.lower().strip() == key.lower().strip():
                    return spec_val
        return None

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract the Whydud category slug from a Flipkart search URL."""
        from urllib.parse import parse_qs, urlparse

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            keyword = params.get("q", [None])[0]
            if keyword:
                normalised = keyword.replace("+", " ").strip().lower()
                return KEYWORD_CATEGORY_MAP.get(normalised)
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _json_ld_price(offer: dict) -> Decimal | None:
        """Extract price in paisa from a JSON-LD Offer object.

        JSON-LD prices are in rupees (e.g., ``"price": "24999"`` or ``24999``).
        """
        raw = offer.get("price")
        if raw is None:
            return None
        try:
            rupees = Decimal(str(raw).replace(",", ""))
            if rupees <= 0:
                return None
            return rupees * 100  # → paisa
        except (InvalidOperation, ValueError):
            return None

    @staticmethod
    def _parse_price_text(text: str | None) -> Decimal | None:
        """Parse price text like '₹24,999' to paisa Decimal."""
        if not text:
            return None
        text = text.strip()
        match = PRICE_RE.search(text)
        if not match:
            return None
        cleaned = match.group(0).replace(",", "")
        if not cleaned:
            return None
        try:
            rupees = Decimal(cleaned)
            if rupees <= 0:
                return None
            return rupees * 100
        except InvalidOperation:
            return None

    @staticmethod
    def _high_res_image(url: str) -> str:
        """Upgrade Flipkart image URL to high resolution.

        Flipkart image URLs (hosted on flixcart.com) contain a size segment
        like ``/image/312/312/`` — replace with ``/image/832/832/`` for
        higher resolution.
        """
        return re.sub(r"/image/\d+/\d+/", "/image/832/832/", url)

    @staticmethod
    def _canonical_url(response_url: str, fpid: str) -> str:
        """Build a clean canonical URL for the product.

        Strips tracking params but keeps the product path and FPID.
        """
        # Extract just the path up to and including the FPID
        match = re.search(r"(https://www\.flipkart\.com/.+/p/" + re.escape(fpid) + r")", response_url)
        if match:
            return match.group(1)
        return f"https://www.flipkart.com/product/p/{fpid}"

    def _save_raw_html(self, response, fpid: str) -> str | None:
        """Save response HTML to local filesystem for debugging."""
        try:
            raw_dir = Path(os.environ.get("SCRAPING_RAW_HTML_DIR", "data/raw_html"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"flipkart_{fpid}_{timestamp}.html"
            filepath = raw_dir / filename
            filepath.write_bytes(response.body)
            return str(filepath)
        except OSError as exc:
            self.logger.warning(f"Could not save raw HTML for {fpid}: {exc}")
            return None
