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
