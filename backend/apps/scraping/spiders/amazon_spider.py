"""Amazon.in spider — scrapes product listings, detail pages, prices, and offers.

Two-phase architecture:
  Phase 1 — Listing pages (/s?k=...) use PLAIN HTTP (no Playwright).
            Product links, titles, and basic info are in raw HTML.
            Falls back to Playwright only on CAPTCHA detection.
  Phase 2 — Product detail pages (/dp/ASIN) use Playwright for JS-rendered
            prices, availability, and dynamic content.

Sprint 2, Week 4.
"""
import hashlib
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

ASIN_RE = re.compile(r"/(?:dp|gp/product)/([A-Z0-9]{10})")
PRICE_RE = re.compile(r"[\d,.]+")
RATING_RE = re.compile(r"([\d.]+)\s*out of\s*5")
REVIEW_COUNT_RE = re.compile(r"([\d,]+)\s*(?:rating|review|customer)")

MARKETPLACE_SLUG = "amazon-in"

# ---------------------------------------------------------------------------
# Amazon search keyword → Whydud category slug mapping
#
# Used to auto-assign a Whydud category to products based on which seed URL
# (search keyword) they were scraped from. Keys are the `k=` param value
# from the seed URL, normalised to lowercase with '+' replaced by ' '.
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
    # Cameras
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
    "nas storage": "laptops",
    # Baby & Kids
    "baby strollers": "baby-kids",
    "car seats baby": "baby-kids",
    "baby monitors": "cameras",
    "baby toys": "baby-kids",
    # Car & Bike
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
# Format: (url, max_pages)  — max_pages controls pagination depth per category.
# The rh=n%3A<id> parameter restricts results to a specific Amazon browse node.
# Top 30 high-value categories get 30 pages (~480 products each).
# Remaining 60 categories get 20 pages (~320 products each).

_TOP = 30   # pages for top categories
_STD = 20   # pages for standard categories

SEED_CATEGORY_URLS: list[tuple[str, int]] = [
    # ── Smartphones & Accessories (TOP) ──────────────────────────────────
    ("https://www.amazon.in/s?k=smartphones&rh=n%3A1805560031", _TOP),
    ("https://www.amazon.in/s?k=phone+cases+covers&rh=n%3A4363159031", _STD),
    ("https://www.amazon.in/s?k=screen+protectors&rh=n%3A4363162031", _STD),
    ("https://www.amazon.in/s?k=power+banks&rh=n%3A6612025031", _TOP),
    ("https://www.amazon.in/s?k=mobile+chargers&rh=n%3A4363085031", _STD),
    # ── Computers & Peripherals (TOP) ────────────────────────────────────
    ("https://www.amazon.in/s?k=laptops&rh=n%3A1375424031", _TOP),
    ("https://www.amazon.in/s?k=tablets&rh=n%3A1375458031", _TOP),
    ("https://www.amazon.in/s?k=monitors&rh=n%3A1375425031", _TOP),
    ("https://www.amazon.in/s?k=computer+keyboards&rh=n%3A1375433031", _STD),
    ("https://www.amazon.in/s?k=computer+mouse&rh=n%3A1375433031", _STD),
    ("https://www.amazon.in/s?k=printers&rh=n%3A1375434031", _STD),
    ("https://www.amazon.in/s?k=routers&rh=n%3A1389401031", _STD),
    ("https://www.amazon.in/s?k=external+hard+drives&rh=n%3A1375430031", _STD),
    ("https://www.amazon.in/s?k=pen+drives&rh=n%3A1375430031", _STD),
    ("https://www.amazon.in/s?k=graphics+cards&rh=n%3A1375424031", _STD),
    ("https://www.amazon.in/s?k=webcams&rh=n%3A1389175031", _STD),
    # ── Audio (TOP) ──────────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=headphones&rh=n%3A1388921031", _TOP),
    ("https://www.amazon.in/s?k=earbuds+tws&rh=n%3A1388921031", _TOP),
    ("https://www.amazon.in/s?k=bluetooth+speakers&rh=n%3A1388888031", _TOP),
    ("https://www.amazon.in/s?k=soundbars&rh=n%3A3401801031", _STD),
    ("https://www.amazon.in/s?k=microphones&rh=n%3A3677700031", _STD),
    # ── Wearables (TOP) ──────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=smartwatches&rh=n%3A6284375031", _TOP),
    ("https://www.amazon.in/s?k=fitness+bands&rh=n%3A6284375031", _STD),
    # ── Cameras & Photography ────────────────────────────────────────────
    ("https://www.amazon.in/s?k=cameras&rh=n%3A1389175031", _TOP),
    ("https://www.amazon.in/s?k=camera+lenses&rh=n%3A1389177031", _STD),
    ("https://www.amazon.in/s?k=camera+tripods&rh=n%3A1389181031", _STD),
    ("https://www.amazon.in/s?k=action+cameras&rh=n%3A1389175031", _STD),
    # ── TVs & Entertainment (TOP) ────────────────────────────────────────
    ("https://www.amazon.in/s?k=televisions&rh=n%3A1389396031", _TOP),
    ("https://www.amazon.in/s?k=projectors&rh=n%3A1389396031", _STD),
    ("https://www.amazon.in/s?k=streaming+devices&rh=n%3A1389396031", _STD),
    ("https://www.amazon.in/s?k=tv+wall+mounts&rh=n%3A1389396031", _STD),
    # ── Large Appliances (TOP) ───────────────────────────────────────────
    ("https://www.amazon.in/s?k=refrigerators&rh=n%3A1380369031", _TOP),
    ("https://www.amazon.in/s?k=washing+machines&rh=n%3A1380365031", _TOP),
    ("https://www.amazon.in/s?k=air+conditioners&rh=n%3A1380369031", _TOP),
    ("https://www.amazon.in/s?k=microwave+ovens&rh=n%3A1380367031", _STD),
    ("https://www.amazon.in/s?k=dishwashers&rh=n%3A1380271031", _STD),
    ("https://www.amazon.in/s?k=water+heaters+geysers&rh=n%3A4369221031", _STD),
    ("https://www.amazon.in/s?k=chimneys&rh=n%3A4369280031", _STD),
    # ── Small Appliances ─────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=air+purifiers&rh=n%3A5131299031", _TOP),
    ("https://www.amazon.in/s?k=water+purifiers&rh=n%3A5131300031", _TOP),
    ("https://www.amazon.in/s?k=vacuum+cleaners&rh=n%3A1380263031", _STD),
    ("https://www.amazon.in/s?k=robot+vacuum+cleaners&rh=n%3A1380263031", _STD),
    ("https://www.amazon.in/s?k=mixer+grinders&rh=n%3A1380263031", _STD),
    ("https://www.amazon.in/s?k=induction+cooktops&rh=n%3A1380536031", _STD),
    ("https://www.amazon.in/s?k=electric+kettles&rh=n%3A1380536031", _STD),
    ("https://www.amazon.in/s?k=air+fryers&rh=n%3A1380536031", _STD),
    ("https://www.amazon.in/s?k=coffee+machines&rh=n%3A1380536031", _STD),
    ("https://www.amazon.in/s?k=irons+steamers&rh=n%3A1380267031", _STD),
    ("https://www.amazon.in/s?k=fans&rh=n%3A1380365031", _STD),
    ("https://www.amazon.in/s?k=room+heaters&rh=n%3A1380365031", _STD),
    # ── Personal Care & Grooming (TOP) ───────────────────────────────────
    ("https://www.amazon.in/s?k=trimmers&rh=n%3A1374407031", _TOP),
    ("https://www.amazon.in/s?k=electric+shavers&rh=n%3A1374407031", _STD),
    ("https://www.amazon.in/s?k=hair+dryers&rh=n%3A1374410031", _STD),
    ("https://www.amazon.in/s?k=hair+straighteners&rh=n%3A1374410031", _STD),
    ("https://www.amazon.in/s?k=electric+toothbrushes&rh=n%3A1374413031", _STD),
    # ── Fitness & Sports ─────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=treadmills&rh=n%3A1961623031", _STD),
    ("https://www.amazon.in/s?k=exercise+bikes&rh=n%3A1961623031", _STD),
    ("https://www.amazon.in/s?k=dumbbells+weights&rh=n%3A1961624031", _STD),
    ("https://www.amazon.in/s?k=yoga+mats&rh=n%3A1961624031", _STD),
    # ── Home & Furniture (TOP) ───────────────────────────────────────────
    ("https://www.amazon.in/s?k=mattresses&rh=n%3A1380279031", _TOP),
    ("https://www.amazon.in/s?k=office+chairs&rh=n%3A3553048031", _TOP),
    ("https://www.amazon.in/s?k=study+tables&rh=n%3A3553048031", _STD),
    ("https://www.amazon.in/s?k=beds&rh=n%3A3553048031", _STD),
    ("https://www.amazon.in/s?k=sofas&rh=n%3A3553048031", _STD),
    ("https://www.amazon.in/s?k=shoe+racks&rh=n%3A3553048031", _STD),
    # ── Smart Home & Security (TOP) ──────────────────────────────────────
    ("https://www.amazon.in/s?k=smart+plugs&rh=n%3A1389401031", _STD),
    ("https://www.amazon.in/s?k=smart+bulbs&rh=n%3A1389401031", _STD),
    ("https://www.amazon.in/s?k=security+cameras&rh=n%3A1389175031", _TOP),
    ("https://www.amazon.in/s?k=smart+door+locks&rh=n%3A1389401031", _STD),
    ("https://www.amazon.in/s?k=video+doorbells&rh=n%3A1389401031", _STD),
    # ── Gaming (TOP) ─────────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=gaming+laptops&rh=n%3A1375424031", _TOP),
    ("https://www.amazon.in/s?k=gaming+monitors&rh=n%3A1375425031", _STD),
    ("https://www.amazon.in/s?k=gaming+headsets&rh=n%3A1388921031", _STD),
    ("https://www.amazon.in/s?k=gaming+controllers&rh=n%3A976460031", _STD),
    ("https://www.amazon.in/s?k=gaming+chairs&rh=n%3A3553048031", _STD),
    # ── Storage & Networking ─────────────────────────────────────────────
    ("https://www.amazon.in/s?k=ssd+internal&rh=n%3A1375430031", _STD),
    ("https://www.amazon.in/s?k=memory+cards&rh=n%3A1375430031", _STD),
    ("https://www.amazon.in/s?k=wifi+mesh+systems&rh=n%3A1389401031", _STD),
    ("https://www.amazon.in/s?k=nas+storage&rh=n%3A1375430031", _STD),
    # ── Baby & Kids ──────────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=baby+strollers&rh=n%3A1571274031", _STD),
    ("https://www.amazon.in/s?k=car+seats+baby&rh=n%3A1571274031", _STD),
    ("https://www.amazon.in/s?k=baby+monitors&rh=n%3A1571274031", _STD),
    # ── Car & Bike Accessories ───────────────────────────────────────────
    ("https://www.amazon.in/s?k=dash+cameras&rh=n%3A4772060031", _STD),
    ("https://www.amazon.in/s?k=car+chargers&rh=n%3A4772060031", _STD),
    ("https://www.amazon.in/s?k=car+air+purifiers&rh=n%3A4772060031", _STD),
    ("https://www.amazon.in/s?k=tyre+inflators&rh=n%3A4772060031", _STD),
    # ── Musical Instruments ──────────────────────────────────────────────
    ("https://www.amazon.in/s?k=guitars&rh=n%3A3677697031", _STD),
    ("https://www.amazon.in/s?k=keyboards+pianos&rh=n%3A3677697031", _STD),
    # ── Luggage & Bags ───────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=laptop+bags+backpacks&rh=n%3A2454169031", _STD),
    ("https://www.amazon.in/s?k=suitcases+trolley&rh=n%3A2454169031", _STD),
    ("https://www.amazon.in/s?k=handbags&rh=n%3A2454169031", _STD),
    # ── Additional Small Appliances ──────────────────────────────────────
    ("https://www.amazon.in/s?k=juicer+mixer+grinder", _STD),
    ("https://www.amazon.in/s?k=hand+blenders", _STD),
    ("https://www.amazon.in/s?k=sandwich+makers", _STD),
    ("https://www.amazon.in/s?k=toasters", _STD),
    ("https://www.amazon.in/s?k=rice+cookers", _STD),
    ("https://www.amazon.in/s?k=pressure+cookers", _STD),
    # ── Personal Care (extra) ────────────────────────────────────────────
    ("https://www.amazon.in/s?k=epilators", _STD),
    # ── Fitness (extra) ──────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=gym+equipment", _STD),
    # ── Home & Furniture (extra) ─────────────────────────────────────────
    ("https://www.amazon.in/s?k=dining+tables", _STD),
    ("https://www.amazon.in/s?k=wardrobes", _STD),
    ("https://www.amazon.in/s?k=bean+bags", _STD),
    ("https://www.amazon.in/s?k=curtains", _STD),
    ("https://www.amazon.in/s?k=bedsheets", _STD),
    # ── Smart Home (extra) ───────────────────────────────────────────────
    ("https://www.amazon.in/s?k=smart+speakers", _STD),
    # ── Gaming (extra) ───────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=gaming+consoles", _STD),
    # ── Baby & Kids (extra) ──────────────────────────────────────────────
    ("https://www.amazon.in/s?k=baby+toys", _STD),
    # ── Car & Bike (extra) ───────────────────────────────────────────────
    ("https://www.amazon.in/s?k=car+accessories", _STD),
    ("https://www.amazon.in/s?k=helmet", _STD),
    # ── Books & Stationery ───────────────────────────────────────────────
    ("https://www.amazon.in/s?k=books+bestsellers", _STD),
    ("https://www.amazon.in/s?k=school+bags", _STD),
    # ── Fashion & Accessories ────────────────────────────────────────────
    ("https://www.amazon.in/s?k=sunglasses", _STD),
    ("https://www.amazon.in/s?k=watches+men", _STD),
    ("https://www.amazon.in/s?k=watches+women", _STD),
    # ── Kitchen & Dining ─────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=cookware+sets", _STD),
    ("https://www.amazon.in/s?k=water+bottles", _STD),
    ("https://www.amazon.in/s?k=lunch+boxes", _STD),
    ("https://www.amazon.in/s?k=kitchen+storage", _STD),
    # ── Cameras (extra) ──────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=drones+cameras", _STD),
    # ── Audio (extra) ────────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=home+theatre+systems", _STD),
    # ── Misc ─────────────────────────────────────────────────────────────
    ("https://www.amazon.in/s?k=mobile+holders+stands", _STD),
]

# Default fallback when --max-pages is passed via CLI (overrides all per-category limits).
MAX_LISTING_PAGES = 5


class AmazonIndiaSpider(BaseWhydudSpider):
    """Scrapes Amazon.in with a two-phase approach.

    Phase 1: Listing pages via plain HTTP (fast, ~0.5s per page).
             CAPTCHA triggers automatic promotion to Playwright.
    Phase 2: Product detail pages via Playwright (JS rendering for prices).

    Spider arguments (passed via ``-a``):
      job_id       — UUID of a ScraperJob row to pull config from.
      category_urls — comma-separated override URLs (testing convenience).
      max_pages    — override MAX_LISTING_PAGES (default 5).
      save_html    — "1" to save raw HTML for debugging (default "0").
    """

    name = "amazon_in"
    allowed_domains = ["amazon.in", "www.amazon.in"]

    # Max retries for CAPTCHA pages before giving up on a URL.
    CAPTCHA_MAX_RETRIES = 3

    # Quick mode: only use first N categories when --max-pages <= 3
    QUICK_MODE_CATEGORIES = 10

    custom_settings = {
        **BaseWhydudSpider.custom_settings,
        "DOWNLOAD_DELAY": 1.5,
        "CONCURRENT_REQUESTS": 8,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 4,
        "RETRY_TIMES": 2,
        "RETRY_HTTP_CODES": [500, 502, 503, 504, 408, 429],
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
        self._pages_followed: dict[str, int] = {}   # base_url → pages followed
        self._max_pages_map: dict[str, int] = {}     # base_url → per-category limit

        # Proxy mode: rotating proxies get fewer CAPTCHA retries (new IP each time)
        self._is_rotating = (
            os.environ.get("SCRAPING_PROXY_TYPE", "static").lower() == "rotating"
        )

        # Scrape stats
        self._listing_pages_scraped: int = 0
        self._product_pages_scraped: int = 0
        self._captcha_count: int = 0
        self._products_extracted: int = 0

    def closed(self, reason):
        """Log final scrape statistics."""
        total = self._product_pages_scraped + self.items_failed
        rate = (self._product_pages_scraped / total * 100) if total > 0 else 0
        self.logger.info(
            f"Amazon spider finished ({reason}): "
            f"listings={self._listing_pages_scraped}, "
            f"product_attempts={total}, "
            f"products_ok={self._product_pages_scraped} ({rate:.0f}%), "
            f"captchas={self._captcha_count}, "
            f"failed={self.items_failed}"
        )

    # ------------------------------------------------------------------
    # start_requests — Phase 1: plain HTTP for listings
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
        """Emit plain HTTP requests for all category listing pages.

        Listing pages don't need Playwright — product links and titles
        are in raw HTML. This cuts download time from ~5-8s to ~0.5s per page.
        Categories are shuffled to distribute load across browse nodes.
        """
        url_pairs = self._load_urls()
        random.shuffle(url_pairs)

        for url, max_pg in url_pairs:
            base = url.split("&page=")[0].split("?page=")[0]
            self._max_pages_map[base] = max_pg

            self.logger.info(f"Queuing category ({max_pg} pages): {url}")
            # Phase 1: NO playwright — plain HTTP for listing pages
            yield scrapy.Request(
                url,
                callback=self.parse_listing_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta={"category_slug": self._resolve_category_from_url(url)},
                dont_filter=True,
            )

        self.logger.info(f"Queued {len(url_pairs)} categories (plain HTTP)")

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
                self.logger.info(f"Running for job {self.job_id}, marketplace: {job.marketplace.slug}")
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
        """Extract product links from a search results page (plain HTTP).

        If Amazon serves a CAPTCHA, promote this page to Playwright and retry.
        """
        self._listing_pages_scraped += 1

        # CAPTCHA detection — promote to Playwright on CAPTCHA
        if self._is_captcha_page(response):
            self._captcha_count += 1
            retries = response.meta.get("captcha_retries", 0)
            if retries < self.CAPTCHA_MAX_RETRIES:
                self.logger.info(
                    f"CAPTCHA on listing {response.url} — promoting to Playwright "
                    f"(retry {retries + 1}/{self.CAPTCHA_MAX_RETRIES})"
                )
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={
                        "playwright": True,
                        "playwright_page_init_callback": self._apply_stealth,
                        "category_slug": response.meta.get("category_slug"),
                        "captcha_retries": retries + 1,
                        "download_delay": 5 * (retries + 1) + random.uniform(2, 5),
                    },
                    dont_filter=True,
                    priority=-1,
                )
            else:
                self.logger.warning(
                    f"CAPTCHA persists after {retries} retries on listing — skipping {response.url}"
                )
            return

        results = response.css('div[data-component-type="s-search-result"]')

        if not results:
            self.logger.warning(f"No search results found on {response.url}")
            return

        self.logger.info(f"Found {len(results)} results on {response.url}")

        category_slug = response.meta.get("category_slug") or self._resolve_category_from_url(response.url)

        for result in results:
            # Amazon 2025+: product link lives in div[data-cy="title-recipe"]
            # or as a.a-link-normal sibling to h2, no longer inside h2.
            link = result.css('div[data-cy="title-recipe"] a::attr(href)').get()
            if not link:
                link = result.css('a.a-link-normal[href*="/dp/"]::attr(href)').get()
            if not link:
                link = result.css("h2 a.a-link-normal::attr(href)").get()
            if not link:
                link = result.css("h2 a::attr(href)").get()
            if not link:
                continue

            # Only follow actual product links (contain /dp/)
            full_url = response.urljoin(link)
            if "/dp/" not in full_url and "/gp/product/" not in full_url:
                continue

            # Phase 2: Product pages USE Playwright (JS-rendered prices)
            # No proxy_session — let middleware round-robin per request
            meta = {
                "playwright": True,
                "playwright_page_init_callback": self._apply_stealth,
                "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                "playwright_page_methods": [
                    PageMethod("wait_for_load_state", "domcontentloaded"),
                    PageMethod("wait_for_timeout", random.randint(2500, 5000)),
                ],
                "category_slug": category_slug,
            }
            yield scrapy.Request(
                full_url,
                callback=self.parse_product_page,
                errback=self.handle_error,
                headers=self._make_headers(),
                meta=meta,
            )

        # Pagination — follow "Next" link up to per-category max_pages (plain HTTP)
        base_url = response.url.split("&page=")[0].split("?page=")[0]
        pages_so_far = self._pages_followed.get(base_url, 1)
        max_for_category = self._max_pages_map.get(base_url, MAX_LISTING_PAGES)
        if pages_so_far < max_for_category:
            next_link = response.css("a.s-pagination-next::attr(href)").get()
            if next_link:
                self._pages_followed[base_url] = pages_so_far + 1
                # Stay in plain HTTP for next listing page
                yield scrapy.Request(
                    response.urljoin(next_link),
                    callback=self.parse_listing_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta={"category_slug": category_slug},
                )

    # ------------------------------------------------------------------
    # Phase 2: Product detail page (Playwright)
    # ------------------------------------------------------------------

    def _is_captcha_page(self, response) -> bool:
        """Detect if Amazon served a CAPTCHA / bot-check page."""
        page_title = response.css("title::text").get() or ""
        if page_title.strip().lower() in ("amazon.in", "robot check", ""):
            return True
        if response.css("form[action*='validateCaptcha']"):
            return True
        if b"captcha" in response.body[:5000].lower():
            return True
        return False

    def parse_product_page(self, response):
        """Extract all product data from an Amazon.in product detail page."""
        self._product_pages_scraped += 1

        # Check middleware's CAPTCHA flag first (rotating proxy already detected it)
        if response.meta.get("_rotating_proxy_captcha"):
            self._captcha_count += 1
            self.items_failed += 1
            self.logger.debug(
                f"CAPTCHA flagged by proxy middleware — skipping {response.url[:60]}"
            )
            return

        # --- CAPTCHA detection & retry ---
        retries = response.meta.get("captcha_retries", 0)
        if self._is_captcha_page(response):
            self._captcha_count += 1

            # With rotating proxies, retry ONCE (next request gets new IP).
            # With static/no proxies, retry up to CAPTCHA_MAX_RETRIES.
            max_retries = 1 if self._is_rotating else self.CAPTCHA_MAX_RETRIES

            if retries < max_retries:
                self.logger.info(
                    f"CAPTCHA on {response.url} — retry {retries + 1}/{max_retries}"
                )
                meta = {
                    "playwright": True,
                    "playwright_page_init_callback": self._apply_stealth,
                    "playwright_page_goto_kwargs": {"wait_until": "domcontentloaded"},
                    "playwright_page_methods": [
                        PageMethod("wait_for_load_state", "domcontentloaded"),
                        PageMethod("wait_for_timeout", random.randint(3000, 6000)),
                    ],
                    "category_slug": response.meta.get("category_slug"),
                    "captcha_retries": retries + 1,
                }
                yield scrapy.Request(
                    response.url,
                    callback=self.parse_product_page,
                    errback=self.handle_error,
                    headers=self._make_headers(),
                    meta=meta,
                    dont_filter=True,
                    priority=-1,
                )
                return

            # Max retries reached — skip this product
            self.logger.info(f"Skipping {response.url} after {retries} CAPTCHA retries")
            self.items_failed += 1
            return

        asin = self._extract_asin(response)
        if not asin:
            self.logger.warning(f"Could not extract ASIN from {response.url}")
            self.items_failed += 1
            return

        # Save raw HTML for debugging BEFORE extraction (so we can debug failures)
        raw_html_path = None
        if self._save_html:
            raw_html_path = self._save_raw_html(response, asin)

        title = self._extract_title(response, asin)
        if not title:
            self.logger.warning(f"No title found for ASIN {asin} — page length={len(response.text)}")
            self.items_failed += 1
            return

        item = ProductItem()
        item["marketplace_slug"] = MARKETPLACE_SLUG
        item["external_id"] = asin
        item["url"] = self._canonical_url(asin)
        item["title"] = title
        item["brand"] = self._extract_brand(response)
        item["price"] = self._extract_price(response)
        item["mrp"] = self._extract_mrp(response)
        item["images"] = self._extract_images(response)
        item["rating"] = self._extract_rating(response)
        item["review_count"] = self._extract_review_count(response)
        item["specs"] = self._extract_specs(response)
        item["seller_name"] = self._extract_seller(response)
        item["seller_rating"] = None  # Amazon doesn't always expose seller rating on product page
        item["in_stock"] = self._extract_availability(response)
        item["fulfilled_by"] = self._extract_fulfilled_by(response)
        item["category_slug"] = response.meta.get("category_slug")
        item["about_bullets"] = self._extract_about_bullets(response)
        item["offer_details"] = self._extract_offers(response)
        item["raw_html_path"] = raw_html_path

        # Extended fields — comprehensive product info
        item["description"] = self._extract_description(response)
        item["warranty"] = self._extract_warranty(response)
        item["delivery_info"] = self._extract_delivery_info(response)
        item["return_policy"] = self._extract_return_policy(response)
        item["breadcrumbs"] = self._extract_breadcrumbs(response)
        item["variant_options"] = self._extract_variants(response)
        item["country_of_origin"] = self._extract_from_specs(item["specs"], ["Country of Origin", "country of origin"])
        item["manufacturer"] = self._extract_from_specs(item["specs"], ["Manufacturer", "manufacturer"])
        item["model_number"] = self._extract_from_specs(item["specs"], ["Item model number", "Model Number", "Model Name", "model number"])
        item["weight"] = self._extract_from_specs(item["specs"], ["Item Weight", "Product Weight", "Weight", "item weight"])
        item["dimensions"] = self._extract_from_specs(item["specs"], ["Product Dimensions", "Item Dimensions", "Dimensions", "product dimensions"])

        self.items_scraped += 1
        self._products_extracted += 1
        yield item

    # ------------------------------------------------------------------
    # Field extraction helpers
    # ------------------------------------------------------------------

    def _extract_asin(self, response) -> str | None:
        """Extract ASIN from URL or page data attributes."""
        # Try URL first
        match = ASIN_RE.search(response.url)
        if match:
            return match.group(1)
        # Try hidden input
        asin = response.css('input[name="ASIN"]::attr(value)').get()
        if asin:
            return asin.strip()
        # Try data attribute on body or product div
        asin = response.css("#ASIN::attr(value)").get()
        return asin.strip() if asin else None

    def _extract_title(self, response, asin: str = "") -> str | None:
        """Extract product title from multiple sources in priority order.

        Tries 7 methods to maximize resilience against Amazon layout changes.
        Logs which method succeeded for debugging.
        """
        # Method 1: #productTitle (most common)
        title = response.css("#productTitle::text").get()
        if title and title.strip():
            self.logger.debug(f"Title for {asin} extracted via method 1 (#productTitle)")
            return title.strip()

        # Method 2: #title span
        title = response.css("#title span::text").get()
        if title and title.strip():
            self.logger.debug(f"Title for {asin} extracted via method 2 (#title span)")
            return title.strip()

        # Method 3: h1#title span.a-text-normal
        title = response.css("h1#title span.a-text-normal::text").get()
        if title and title.strip():
            self.logger.debug(f"Title for {asin} extracted via method 3 (h1#title span.a-text-normal)")
            return title.strip()

        # Method 4: any h1 span
        title = response.css("h1 span::text").get()
        if title and title.strip():
            self.logger.debug(f"Title for {asin} extracted via method 4 (h1 span)")
            return title.strip()

        # Method 5: JSON-LD Product schema
        for script in response.css('script[type="application/ld+json"]::text').getall():
            try:
                data = json.loads(script)
                # Handle both single object and array of objects
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "Product" and item.get("name"):
                        self.logger.debug(f"Title for {asin} extracted via method 5 (JSON-LD)")
                        return item["name"].strip()
            except (json.JSONDecodeError, KeyError, TypeError):
                continue

        # Method 6: Open Graph og:title
        og_title = response.css('meta[property="og:title"]::attr(content)').get()
        if og_title and og_title.strip():
            self.logger.debug(f"Title for {asin} extracted via method 6 (og:title)")
            return og_title.strip()

        # Method 7: <title> tag — strip " : Amazon.in" suffix
        page_title = response.css("title::text").get()
        if page_title:
            cleaned = re.sub(r"\s*[:\-|]\s*Amazon\.in.*$", "", page_title.strip())
            cleaned = re.sub(r"^Amazon\.in\s*[:\-|]\s*", "", cleaned)
            if cleaned and len(cleaned) > 5 and cleaned.lower() != "amazon.in":
                self.logger.debug(f"Title for {asin} extracted via method 7 (<title> tag)")
                return cleaned

        return None

    def _extract_brand(self, response) -> str | None:
        """Extract brand name from byline or tech specs."""
        # Primary: byline link
        byline = response.css("a#bylineInfo::text").get()
        if byline:
            # "Visit the Samsung Store" → "Samsung"
            byline = byline.strip()
            byline = re.sub(r"^Visit the\s+", "", byline, flags=re.IGNORECASE)
            byline = re.sub(r"\s+Store$", "", byline, flags=re.IGNORECASE)
            byline = re.sub(r"^Brand:\s*", "", byline, flags=re.IGNORECASE)
            if byline:
                return byline

        # Fallback: tech specs table
        for row in response.css("#productDetails_techSpec_section_1 tr"):
            label = row.css("th::text").get("").strip().lower()
            if label in ("brand", "manufacturer"):
                return row.css("td::text").get("").strip()

        return None

    def _extract_price(self, response) -> Decimal | None:
        """Extract current sale price in paisa."""
        selectors = [
            # Core price display (desktop)
            '#corePriceDisplay_desktop_feature_div .a-price .a-offscreen::text',
            # Deal price
            '#dealprice_feature_div .a-price .a-offscreen::text',
            # Apex price
            '#apex_desktop .a-price .a-offscreen::text',
            # Generic first .a-price on page
            'span.a-price span.a-offscreen::text',
            # Legacy selectors
            '#priceblock_dealprice::text',
            '#priceblock_ourprice::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price
        return None

    def _extract_mrp(self, response) -> Decimal | None:
        """Extract MRP (maximum retail price) in paisa."""
        selectors = [
            '.basisPrice .a-text-price span.a-offscreen::text',
            '#corePriceDisplay_desktop_feature_div .a-text-price span.a-offscreen::text',
            'span.a-text-price span.a-offscreen::text',
            '#listPrice::text',
            '#priceblock_listprice::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            price = self._parse_price_text(text)
            if price is not None:
                return price
        return None

    def _extract_images(self, response) -> list[str]:
        """Extract all product image URLs (full resolution)."""
        images: list[str] = []

        # Primary: landing/main image
        main_img = response.css("#landingImage::attr(data-old-hires)").get()
        if not main_img:
            main_img = response.css("#landingImage::attr(src)").get()
        if not main_img:
            main_img = response.css("#imgBlkFront::attr(src)").get()
        if main_img and "placeholder" not in main_img:
            images.append(self._full_res_image(main_img))

        # Alt images (thumbnail strip)
        for img in response.css("#altImages .a-button-text img::attr(src)").getall():
            if "placeholder" in img or "icon" in img:
                continue
            full = self._full_res_image(img)
            if full not in images:
                images.append(full)

        # Fallback: try data-a-dynamic-image JSON on landing image
        if not images:
            dynamic = response.css("#landingImage::attr(data-a-dynamic-image)").get()
            if dynamic:
                try:
                    url_map = json.loads(dynamic)
                    # Keys are URLs, values are [width, height] — pick largest
                    sorted_urls = sorted(url_map.items(), key=lambda x: x[1][0], reverse=True)
                    for url, _ in sorted_urls[:6]:
                        images.append(url)
                except (ValueError, KeyError):
                    pass

        return images[:10]  # cap at 10 images

    def _extract_rating(self, response) -> Decimal | None:
        """Extract average star rating (0-5)."""
        selectors = [
            '#acrPopover span.a-icon-alt::text',
            'span[data-hook="rating-out-of-text"]::text',
            '#averageCustomerReviews .a-icon-alt::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            if text:
                match = RATING_RE.search(text)
                if match:
                    try:
                        return Decimal(match.group(1))
                    except InvalidOperation:
                        pass
        return None

    def _extract_review_count(self, response) -> int | None:
        """Extract total number of ratings/reviews."""
        selectors = [
            '#acrCustomerReviewText::text',
            'span[data-hook="total-review-count"] span::text',
            '#acrCustomerReviewLink span::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            if text:
                match = REVIEW_COUNT_RE.search(text)
                if match:
                    return int(match.group(1).replace(",", ""))
        return None

    def _extract_seller(self, response) -> str | None:
        """Extract seller name."""
        selectors = [
            '#sellerProfileTriggerId::text',
            '#merchant-info a::text',
            '#tabular-buybox .tabular-buybox-text[tabular-attribute-name="Sold by"] span::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        return None

    def _extract_availability(self, response) -> bool:
        """Determine if product is in stock."""
        avail_text = response.css("#availability span.a-size-medium::text").get()
        if not avail_text:
            avail_text = response.css("#availability span::text").get()
        if avail_text:
            avail_lower = avail_text.strip().lower()
            if "in stock" in avail_lower:
                return True
            if "currently unavailable" in avail_lower or "out of stock" in avail_lower:
                return False
        # If we found a price, assume in stock
        return self._extract_price(response) is not None

    def _extract_fulfilled_by(self, response) -> str | None:
        """Extract fulfilment info (Amazon or third-party)."""
        selectors = [
            '#tabular-buybox .tabular-buybox-text[tabular-attribute-name="Ships from"] span::text',
            '#SSOFp498_feature_div span::text',
        ]
        for sel in selectors:
            text = response.css(sel).get()
            if text and text.strip():
                return text.strip()
        # Check for "Fulfilled by Amazon" badge
        fba = response.css("#deliveryBlockMessage .a-text-bold::text").get()
        if fba and "amazon" in fba.lower():
            return "Amazon"
        return None

    def _extract_specs(self, response) -> dict[str, str]:
        """Extract technical specifications as key-value pairs."""
        specs: dict[str, str] = {}

        # Primary: tech spec table
        for row in response.css("#productDetails_techSpec_section_1 tr"):
            key = row.css("th::text").get("").strip()
            val = row.css("td::text").get("").strip()
            if key and val:
                specs[key] = val

        # Fallback: additional info table
        for row in response.css("#productDetails_detailBullets_sections1 tr"):
            key = row.css("th::text").get("").strip()
            val = row.css("td::text").get("").strip()
            if key and val:
                specs[key] = val

        # Fallback: detail bullets (flat list)
        if not specs:
            for li in response.css("#detailBullets_feature_div li"):
                text = li.css("span.a-list-item::text").getall()
                # Format: ["Key\n", "Value\n"]
                parts = [t.strip() for t in text if t.strip()]
                if len(parts) >= 2:
                    key = parts[0].rstrip(" :\u200f\u200e")
                    val = parts[1].lstrip(" :\u200f\u200e")
                    if key and val:
                        specs[key] = val

        return specs

    def _extract_about_bullets(self, response) -> list[str]:
        """Extract 'About this item' bullet points."""
        bullets: list[str] = []
        for span in response.css("#feature-bullets ul li span.a-list-item::text").getall():
            text = span.strip()
            if text and not text.startswith("›"):
                bullets.append(text)
        return bullets

    def _extract_offers(self, response) -> list[dict]:
        """Extract bank offers, coupons, and EMI details."""
        offers: list[dict] = []

        # Bank offers section
        for offer_div in response.css("#sopp_feature_div .a-row, #itembox-InstallmentCalculator .a-row"):
            text = offer_div.css("::text").getall()
            offer_text = " ".join(t.strip() for t in text if t.strip())
            if not offer_text or len(offer_text) < 10:
                continue
            offer = {"text": offer_text[:500]}

            # Try to identify offer type
            lower = offer_text.lower()
            if "cashback" in lower:
                offer["type"] = "cashback"
            elif "emi" in lower or "no cost emi" in lower:
                offer["type"] = "emi"
            elif "coupon" in lower:
                offer["type"] = "coupon"
            elif "bank" in lower or "card" in lower:
                offer["type"] = "bank_offer"
            else:
                offer["type"] = "other"

            offers.append(offer)

        return offers[:10]  # cap at 10

    # ------------------------------------------------------------------
    # Extended field extraction (description, warranty, delivery, etc.)
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_description(response) -> str | None:
        """Extract product description from the product overview or description section."""
        # Primary: product description section
        desc_parts = response.css("#productDescription p::text, #productDescription span::text").getall()
        if desc_parts:
            return " ".join(t.strip() for t in desc_parts if t.strip())[:5000]

        # Fallback: product overview feature div
        overview = response.css("#productOverview_feature_div td::text").getall()
        if overview:
            return " | ".join(t.strip() for t in overview if t.strip())[:5000]

        # Fallback: A+ content / brand story
        aplus = response.css("#aplus p::text, #aplus span::text").getall()
        if aplus:
            return " ".join(t.strip() for t in aplus if t.strip())[:5000]

        return None

    @staticmethod
    def _extract_warranty(response) -> str | None:
        """Extract warranty information."""
        # Look for warranty in specs table
        for row in response.css("#productDetails_techSpec_section_1 tr, #productDetails_detailBullets_sections1 tr"):
            label = row.css("th::text").get("").strip().lower()
            if "warranty" in label:
                return row.css("td::text").get("").strip()

        # Look for warranty in product information table
        for row in response.css("#productDetails_db_sections tr"):
            label = row.css("th::text").get("").strip().lower()
            if "warranty" in label:
                return row.css("td::text").get("").strip()

        # Look in detail bullets
        for li in response.css("#detailBullets_feature_div li"):
            text = " ".join(li.css("span::text").getall()).lower()
            if "warranty" in text:
                parts = [t.strip() for t in li.css("span::text").getall() if t.strip()]
                if len(parts) >= 2:
                    return parts[-1]

        return None

    @staticmethod
    def _extract_delivery_info(response) -> str | None:
        """Extract delivery estimate from the page."""
        # Primary: delivery message
        delivery = response.css("#deliveryBlockMessage .a-text-bold::text").get()
        if delivery and delivery.strip():
            return delivery.strip()

        # Fallback: delivery date text
        delivery = response.css("#mir-layout-DELIVERY_BLOCK-slot-PRIMARY_DELIVERY_MESSAGE_LARGE span::text").get()
        if delivery and delivery.strip():
            return delivery.strip()

        delivery = response.css("#delivery-promise-text span::text").get()
        return delivery.strip() if delivery else None

    @staticmethod
    def _extract_return_policy(response) -> str | None:
        """Extract return policy text."""
        for sel in [
            '#productSupportAndReturnPolicy-return_policy_feature_div span::text',
            '#returnPolicyFeature_feature_div span::text',
        ]:
            text = response.css(sel).get()
            if text and text.strip() and len(text.strip()) > 5:
                return text.strip()
        return None

    @staticmethod
    def _extract_breadcrumbs(response) -> list[str]:
        """Extract navigation breadcrumb trail."""
        crumbs = response.css("#wayfinding-breadcrumbs_feature_div ul li a::text").getall()
        return [c.strip() for c in crumbs if c.strip()]

    @staticmethod
    def _extract_variants(response) -> list[dict]:
        """Extract available variant options (color, size, storage, etc.)."""
        variants: list[dict] = []

        # Color/pattern variants
        for swatch in response.css("#variation_color_name li"):
            label = swatch.css("img::attr(alt)").get() or swatch.css("::attr(title)").get()
            if label:
                variant = {"type": "color", "value": label.strip()}
                asin = swatch.css("::attr(data-defaultasin)").get()
                if asin:
                    variant["asin"] = asin
                variants.append(variant)

        # Size/storage variants
        for swatch in response.css("#variation_size_name li, #variation_style_name li"):
            label = swatch.css(".a-size-base::text").get() or swatch.css("::attr(title)").get()
            if label:
                variant = {"type": "size", "value": label.strip()}
                asin = swatch.css("::attr(data-defaultasin)").get()
                if asin:
                    variant["asin"] = asin
                variants.append(variant)

        return variants[:30]  # cap at 30 variants

    @staticmethod
    def _extract_from_specs(specs: dict, keys: list[str]) -> str | None:
        """Extract a specific value from the specs dict by trying multiple key names."""
        if not specs:
            return None
        for key in keys:
            if key in specs:
                return specs[key]
            # Case-insensitive fallback
            for spec_key, spec_val in specs.items():
                if spec_key.lower().strip() == key.lower().strip():
                    return spec_val
        return None

    # ------------------------------------------------------------------
    # Category resolution
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_category_from_url(url: str) -> str | None:
        """Extract the Whydud category slug from an Amazon search URL.

        Parses the `k=` query parameter and looks it up in KEYWORD_CATEGORY_MAP.
        """
        from urllib.parse import parse_qs, urlparse

        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            keyword = params.get("k", [None])[0]
            if keyword:
                # Normalise: "phone+cases+covers" → "phone cases covers"
                normalised = keyword.replace("+", " ").strip().lower()
                return KEYWORD_CATEGORY_MAP.get(normalised)
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Parsing utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_price_text(text: str | None) -> Decimal | None:
        """Parse price text like '₹24,999' or '₹1,24,999.00' to paisa Decimal.

        Returns None if text is empty or unparseable.
        """
        if not text:
            return None
        text = text.strip()
        # Extract numeric portion (digits, commas, dots)
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
            return rupees * 100  # convert to paisa
        except InvalidOperation:
            return None

    @staticmethod
    def _full_res_image(url: str) -> str:
        """Convert Amazon thumbnail URL to full-resolution version.

        Amazon image URLs contain size tokens like '_SS40_', '_SX300_', '_SL1500_'.
        Replace with a high-res token.
        """
        return re.sub(r"\._[A-Z]{2}\d+_\.", "._SL1500_.", url)

    @staticmethod
    def _canonical_url(asin: str) -> str:
        """Build a clean canonical URL for an ASIN."""
        return f"https://www.amazon.in/dp/{asin}"

    def _save_raw_html(self, response, asin: str) -> str | None:
        """Save response HTML to local filesystem for debugging."""
        try:
            raw_dir = Path(os.environ.get("SCRAPING_RAW_HTML_DIR", "data/raw_html"))
            raw_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"amazon_{asin}_{timestamp}.html"
            filepath = raw_dir / filename
            filepath.write_bytes(response.body)
            return str(filepath)
        except OSError as exc:
            self.logger.warning(f"Could not save raw HTML for {asin}: {exc}")
            return None
