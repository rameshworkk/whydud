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
