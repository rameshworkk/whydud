"""Configuration for the price history backfill pipeline.

All values are overridable via Django settings / env vars.
Uses the same ``_get()`` accessor as ``common/app_settings.py``.
"""
from common.app_settings import _get


class BackfillConfig:
    """Tunable settings for the backfill pipeline."""

    # ── BuyHatke API ─────────────────────────────────────────────

    @classmethod
    def bh_base_url(cls) -> str:
        return _get("BACKFILL_BH_BASE_URL", "https://graph.bitbns.com")

    @classmethod
    def bh_compare_url(cls) -> str:
        return _get("BACKFILL_BH_COMPARE_URL", "https://search-new.bitbns.com")

    @classmethod
    def bh_delay(cls) -> float:
        """Seconds between BuyHatke requests."""
        return float(_get("BACKFILL_BH_DELAY", 0.5))

    @classmethod
    def bh_concurrency(cls) -> int:
        """Max concurrent BuyHatke requests (asyncio.Semaphore)."""
        return int(_get("BACKFILL_BH_CONCURRENCY", 5))

    @classmethod
    def bh_timeout(cls) -> float:
        """HTTP timeout for BuyHatke requests in seconds."""
        return float(_get("BACKFILL_BH_TIMEOUT", 15.0))

    @classmethod
    def bh_max_retries(cls) -> int:
        return int(_get("BACKFILL_BH_MAX_RETRIES", 3))

    # ── PriceHistory.app ─────────────────────────────────────────

    @classmethod
    def ph_base_url(cls) -> str:
        return _get("BACKFILL_PH_BASE_URL", "https://pricehistory.app")

    @classmethod
    def ph_html_delay(cls) -> float:
        """Seconds between PH HTML page fetches."""
        return float(_get("BACKFILL_PH_HTML_DELAY", 0.5))

    @classmethod
    def ph_api_delay(cls) -> float:
        """Seconds between PH API calls (token + data)."""
        return float(_get("BACKFILL_PH_API_DELAY", 1.5))

    @classmethod
    def ph_concurrency(cls) -> int:
        """Max concurrent PH requests."""
        return int(_get("BACKFILL_PH_CONCURRENCY", 5))

    @classmethod
    def ph_timeout(cls) -> float:
        return float(_get("BACKFILL_PH_TIMEOUT", 30.0))

    # ── Batch sizes ──────────────────────────────────────────────

    @classmethod
    def inject_batch_size(cls) -> int:
        """Rows per batch INSERT into price_snapshots."""
        return int(_get("BACKFILL_INJECT_BATCH_SIZE", 1000))

    @classmethod
    def phase0_batch_size(cls) -> int:
        return int(_get("BACKFILL_PHASE0_BATCH_SIZE", 2000))

    @classmethod
    def phase2_batch_size(cls) -> int:
        return int(_get("BACKFILL_PHASE2_BATCH_SIZE", 5000))

    @classmethod
    def phase3_limit(cls) -> int:
        return int(_get("BACKFILL_PHASE3_LIMIT", 5000))

    # ── BuyHatke marketplace pos mapping ─────────────────────────
    # Our marketplace slug → BuyHatke ``pos`` parameter.
    # Source: BuyHatke Chrome Extension API Recon (docs/BuyHatke...md)

    @classmethod
    def bh_pos_map(cls) -> dict[str, int]:
        """Our marketplace slug → BuyHatke pos ID."""
        return _get(
            "BACKFILL_BH_POS_MAP",
            {
                "amazon-in": 63,
                "flipkart": 2,
                "croma": 71,
                "myntra": 111,
                "snapdeal": 129,
                "nykaa": 1830,
                "ajio": 2191,
                "tata-cliq": 2190,
                "jiomart": 6660,
                "reliance-digital": 6607,
                "vijay-sales": 6645,
            },
        )

    # ── Targeted scraping ───────────────────────────────────────

    @classmethod
    def product_url_map(cls) -> dict[str, str]:
        """Marketplace slug → product URL template. Use {pid} placeholder."""
        return _get(
            "BACKFILL_PRODUCT_URL_MAP",
            {
                "amazon-in": "https://www.amazon.in/dp/{pid}",
                "flipkart": "https://www.flipkart.com/p/{pid}",
            },
        )

    @classmethod
    def scrape_batch_size(cls) -> int:
        """Product URLs per spider subprocess batch."""
        return int(_get("BACKFILL_SCRAPE_BATCH_SIZE", 50))

    @classmethod
    def scrape_max_retries(cls) -> int:
        """Max scrape attempts before deprioritizing a product."""
        return int(_get("BACKFILL_SCRAPE_MAX_RETRIES", 3))

    # ── PH sitemap discovery ─────────────────────────────────────

    @classmethod
    def electronics_keywords(cls) -> list[str]:
        """Keywords for filtering electronics/tech products from PH sitemap slugs."""
        return _get(
            "BACKFILL_ELECTRONICS_KEYWORDS",
            [
                # Phones
                "iphone", "samsung", "galaxy", "oneplus", "pixel", "redmi",
                "realme", "poco", "vivo", "oppo", "nothing", "motorola",
                "nokia", "iqoo", "xiaomi",
                # Laptops
                "laptop", "macbook", "thinkpad", "ideapad", "vivobook",
                "inspiron", "chromebook", "zenbook", "pavilion", "legion",
                # Audio
                "headphone", "earbuds", "earphone", "airpods", "buds",
                "neckband", "speaker", "soundbar", "jbl-", "sony-wh", "bose-",
                # Wearables
                "smartwatch", "watch-", "apple-watch", "galaxy-watch",
                # TVs & Displays
                "television", "-tv-", "monitor", "smart-tv", "oled", "qled",
                # Appliances
                "refrigerator", "fridge", "washing-machine", "air-conditioner",
                "air-purifier", "water-purifier", "microwave", "dishwasher",
                # Other electronics
                "camera", "gopro", "tablet", "ipad", "router", "powerbank",
                "power-bank", "charger", "ssd", "hard-disk", "trimmer",
                "printer", "projector", "kindle", "playstation", "ps5",
                "xbox", "nintendo", "gaming",
            ],
        )
