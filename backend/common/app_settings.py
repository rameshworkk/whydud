"""Configurable application settings accessor.

All runtime-tunable values are read through this module — never from raw
``django.conf.settings`` or hardcoded literals in views/serializers.

Pattern:
  - Django settings (base.py / env vars) define the defaults.
  - Sprint 4 SiteConfiguration admin model will override these at runtime
    by writing to a cached key that each accessor checks first.
  - Views and pagination classes import from here exclusively.

Adding a new tunable:
  1. Add an env-driven constant to ``settings/base.py``.
  2. Add a classmethod below that reads it via ``_get()``.
  3. The admin panel (Sprint 4) only needs to know the string key to expose it.
"""
from django.conf import settings


def _get(key: str, default):
    """Return ``settings.<key>`` when present, otherwise ``default``."""
    return getattr(settings, key, default)


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------

class PaginationConfig:
    """Global cursor-pagination defaults (used by the base CursorPagination)."""

    @classmethod
    def page_size(cls) -> int:
        return _get("PAGINATION_PAGE_SIZE", 20)

    @classmethod
    def max_page_size(cls) -> int:
        return _get("PAGINATION_MAX_PAGE_SIZE", 100)


# ---------------------------------------------------------------------------
# Product list
# ---------------------------------------------------------------------------

class ProductConfig:
    """Configurable values for product list/filter endpoints."""

    @classmethod
    def page_size(cls) -> int:
        return _get("PRODUCT_LIST_PAGE_SIZE", 24)

    @classmethod
    def max_page_size(cls) -> int:
        return _get("PRODUCT_LIST_PAGE_SIZE_MAX", 100)

    @classmethod
    def default_ordering(cls) -> str:
        """Single-field fallback when sort_map returns an empty list."""
        return _get("PRODUCT_LIST_DEFAULT_ORDERING", "-dud_score")

    @classmethod
    def sort_map(cls) -> dict[str, list[str]]:
        """Maps public ``sort_by`` values to ORM ``order_by()`` expressions."""
        return _get(
            "PRODUCT_SORT_OPTIONS",
            {
                "dud_score": ["-dud_score"],
                "price_asc": ["current_best_price"],
                "price_desc": ["-current_best_price"],
                "newest": ["-created_at"],
                "top_rated": ["-avg_rating"],
            },
        )


# ---------------------------------------------------------------------------
# Search & Autocomplete
# ---------------------------------------------------------------------------

class SearchConfig:
    """Configurable values for search and autocomplete endpoints."""

    @classmethod
    def page_size_default(cls) -> int:
        return _get("SEARCH_PAGE_SIZE_DEFAULT", 20)

    @classmethod
    def page_size_max(cls) -> int:
        return _get("SEARCH_PAGE_SIZE_MAX", 100)

    @classmethod
    def autocomplete_limit(cls) -> int:
        return _get("SEARCH_AUTOCOMPLETE_LIMIT", 8)

    @classmethod
    def min_query_length(cls) -> int:
        return _get("SEARCH_MIN_QUERY_LENGTH", 2)

    @classmethod
    def meili_sort_map(cls) -> dict[str, list[str]]:
        """Maps public ``sort_by`` values to Meilisearch sort expressions."""
        return _get(
            "SEARCH_SORT_MAP_MEILI",
            {
                "relevance": [],
                "price_asc": ["current_best_price:asc"],
                "price_desc": ["current_best_price:desc"],
                "dud_score": ["dud_score:desc"],
                "top_rated": ["avg_rating:desc"],
            },
        )


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

class ScrapingConfig:
    """Configurable values for marketplace scraping."""

    @classmethod
    def spider_timeout(cls) -> int:
        """Max runtime per spider in seconds."""
        return _get("SCRAPING_SPIDER_TIMEOUT", 3600)

    @classmethod
    def max_listing_pages(cls) -> int:
        """Max pagination pages to follow per category."""
        return _get("SCRAPING_MAX_LISTING_PAGES", 5)

    @classmethod
    def raw_html_dir(cls) -> str:
        """Directory to save raw HTML for debugging."""
        return _get("SCRAPING_RAW_HTML_DIR", "data/raw_html")

    @classmethod
    def spider_map(cls) -> dict[str, str]:
        """Marketplace slug → spider name mapping."""
        return _get(
            "SCRAPING_SPIDER_MAP",
            {
                "amazon-in": "amazon_in",
                "flipkart": "flipkart",
            },
        )


# ---------------------------------------------------------------------------
# Product Matching
# ---------------------------------------------------------------------------

class MatchingConfig:
    """Thresholds for the product matching engine (products/matching.py)."""

    @classmethod
    def auto_merge_threshold(cls) -> float:
        """Minimum confidence to auto-merge a listing into an existing product."""
        return _get("MATCHING_AUTO_MERGE_THRESHOLD", 0.85)

    @classmethod
    def review_threshold(cls) -> float:
        """Minimum confidence for manual-review queue.  Below this → new product."""
        return _get("MATCHING_REVIEW_THRESHOLD", 0.60)

    @classmethod
    def fuzzy_title_threshold(cls) -> float:
        """Minimum SequenceMatcher ratio for fuzzy title matching."""
        return _get("MATCHING_FUZZY_TITLE_THRESHOLD", 0.80)

    @classmethod
    def max_candidates(cls) -> int:
        """Max candidate products to evaluate per match attempt."""
        return _get("MATCHING_MAX_CANDIDATES", 500)


# ---------------------------------------------------------------------------
# Email Sending
# ---------------------------------------------------------------------------

class EmailSendConfig:
    """Rate limits and allowed domains for outbound email via Resend."""

    @classmethod
    def daily_send_limit(cls) -> int:
        """Max emails a user can send per day."""
        return _get("EMAIL_SEND_DAILY_LIMIT", 10)

    @classmethod
    def monthly_send_limit(cls) -> int:
        """Max emails a user can send per month."""
        return _get("EMAIL_SEND_MONTHLY_LIMIT", 50)

    @classmethod
    def allowed_marketplace_domains(cls) -> list[str]:
        """Known marketplace domains users can send to (+ subdomains)."""
        return _get(
            "EMAIL_ALLOWED_MARKETPLACE_DOMAINS",
            [
                "amazon.in",
                "flipkart.com",
                "myntra.com",
                "nykaa.com",
                "snapdeal.com",
                "meesho.com",
                "croma.com",
                "ajio.com",
                "tatacliq.com",
                "jiomart.com",
                "reliancedigital.in",
            ],
        )


# ---------------------------------------------------------------------------
# DudScore Computation
# ---------------------------------------------------------------------------

class ScoringConfig:
    """Tunable thresholds for the DudScore calculation engine."""

    @classmethod
    def sentiment_half_life_days(cls) -> int:
        """Exponential decay half-life for review recency weighting."""
        return _get("SCORING_SENTIMENT_HALF_LIFE_DAYS", 90)

    @classmethod
    def verified_purchase_weight(cls) -> float:
        """Weight multiplier for verified-purchase reviews in sentiment calc."""
        return _get("SCORING_VERIFIED_PURCHASE_WEIGHT", 2.0)

    @classmethod
    def price_stability_window_days(cls) -> int:
        """Window for price CoV and stability calculations."""
        return _get("SCORING_PRICE_STABILITY_WINDOW_DAYS", 90)

    @classmethod
    def return_signal_min_datapoints(cls) -> int:
        """Minimum data points before return signal uses real data."""
        return _get("SCORING_RETURN_SIGNAL_MIN_DATAPOINTS", 10)

    @classmethod
    def review_burst_window_days(cls) -> int:
        """Sliding window (days) for review burst detection."""
        return _get("SCORING_REVIEW_BURST_WINDOW_DAYS", 2)

    @classmethod
    def review_burst_fraction(cls) -> float:
        """Fraction of total reviews in burst window to trigger flag."""
        return _get("SCORING_REVIEW_BURST_FRACTION", 0.30)

    @classmethod
    def flash_sale_penalty_threshold(cls) -> int:
        """Number of discount events in window that triggers instability penalty."""
        return _get("SCORING_FLASH_SALE_PENALTY_THRESHOLD", 10)


# ---------------------------------------------------------------------------
# Fraud Detection
# ---------------------------------------------------------------------------

class FraudDetectionConfig:
    """Tunable thresholds for rule-based fake review detection."""

    @classmethod
    def short_review_max_chars(cls) -> int:
        """Reviews shorter than this (with 5-star) are flagged as suspiciously short."""
        return _get("FRAUD_SHORT_REVIEW_MAX_CHARS", 20)

    @classmethod
    def burst_count_threshold(cls) -> int:
        """Number of same-rating reviews in a single day to trigger burst flag."""
        return _get("FRAUD_BURST_COUNT_THRESHOLD", 5)

    @classmethod
    def duplicate_count_threshold(cls) -> int:
        """Minimum duplicate content_hash occurrences to trigger copy-paste flag."""
        return _get("FRAUD_DUPLICATE_COUNT_THRESHOLD", 2)

    @classmethod
    def flag_threshold(cls) -> int:
        """Number of fraud signals required to auto-flag a review."""
        return _get("FRAUD_FLAG_THRESHOLD", 2)

    @classmethod
    def new_account_days(cls) -> int:
        """Accounts younger than this (days) are considered 'new' for pattern checks."""
        return _get("FRAUD_NEW_ACCOUNT_DAYS", 30)


# ---------------------------------------------------------------------------
# Deal Detection
# ---------------------------------------------------------------------------

class DealDetectionConfig:
    """Tunable thresholds for the deal detection engine."""

    @classmethod
    def error_price_ratio(cls) -> float:
        """Current price must be below this fraction of 30-day avg to flag error pricing."""
        return _get("DEAL_ERROR_PRICE_RATIO", 0.50)

    @classmethod
    def genuine_discount_ratio(cls) -> float:
        """Current price must be below this fraction of MRP for genuine discount."""
        return _get("DEAL_GENUINE_DISCOUNT_RATIO", 0.85)

    @classmethod
    def avg_price_window_days(cls) -> int:
        """Number of days to compute the rolling average price."""
        return _get("DEAL_AVG_PRICE_WINDOW_DAYS", 30)

    @classmethod
    def min_snapshots_for_avg(cls) -> int:
        """Minimum price snapshots required before trusting the average."""
        return _get("DEAL_MIN_SNAPSHOTS_FOR_AVG", 3)

    @classmethod
    def batch_size(cls) -> int:
        """Products processed per batch in detect_deals."""
        return _get("DEAL_DETECTION_BATCH_SIZE", 200)


# ---------------------------------------------------------------------------
# Click Tracking
# ---------------------------------------------------------------------------

class ClickTrackingConfig:
    """Tunable settings for affiliate click tracking."""

    @classmethod
    def sub_tag_marketplaces(cls) -> list[str]:
        """Marketplace slugs that support sub-tag tracking params."""
        return _get("CLICK_SUB_TAG_MARKETPLACES", ["amazon_in", "flipkart"])

    @classmethod
    def sub_tag_param(cls, marketplace_slug: str) -> str:
        """URL parameter name for sub-tag per marketplace."""
        params: dict[str, str] = _get("CLICK_SUB_TAG_PARAMS", {
            "amazon_in": "ascsubtag",
            "flipkart": "affExtParam1",
        })
        return params.get(marketplace_slug, "")

    @classmethod
    def valid_source_pages(cls) -> list[str]:
        """Allowed values for source_page field."""
        return _get("CLICK_VALID_SOURCE_PAGES", [
            "product_page", "comparison", "deal", "search", "homepage",
        ])


# ---------------------------------------------------------------------------
# Subscription
# ---------------------------------------------------------------------------

class SubscriptionConfig:
    """Tunable settings for Razorpay subscription plans."""

    @classmethod
    def pro_amount_paisa(cls) -> int:
        """Pro plan price in paisa (₹99 = 9900 paisa)."""
        return _get("SUBSCRIPTION_PRO_AMOUNT_PAISA", 9900)

    @classmethod
    def pro_duration_days(cls) -> int:
        """Number of days a single Pro payment covers."""
        return _get("SUBSCRIPTION_PRO_DURATION_DAYS", 30)

    @classmethod
    def order_cache_ttl(cls) -> int:
        """Seconds to keep a pending Razorpay order in cache (default 30 min)."""
        return _get("SUBSCRIPTION_ORDER_CACHE_TTL", 1800)
