"""Search views — Meilisearch with transparent DB fallback.

All tuneable values (page sizes, autocomplete limit, sort options) are read
from ``common.app_settings.SearchConfig``.  To change them without a deploy,
update the corresponding ``SEARCH_*`` environment variables; Sprint 4 admin
panel will expose them as editable SiteConfig rows.
"""
from decimal import Decimal, InvalidOperation

from django.conf import settings
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import SearchConfig
from common.rate_limiting import AnonSearchThrottle, UserSearchThrottle
from common.throttling import SearchRateThrottle
from common.utils import error_response, success_response


def _meilisearch_client():
    """Return a configured Meilisearch client, or None if unavailable."""
    try:
        import meilisearch
        url = getattr(settings, "MEILISEARCH_URL", None)
        key = getattr(settings, "MEILISEARCH_MASTER_KEY", "")
        if not url:
            return None
        return meilisearch.Client(url, key)
    except ImportError:
        return None


class SearchView(APIView):
    """GET /api/v1/search

    Query params
    ------------
    q         : search query (required)
    category  : category slug filter
    brand     : brand slug filter
    min_price : minimum ``current_best_price`` (paisa)
    max_price : maximum ``current_best_price`` (paisa)
    sort_by   : relevance | price_asc | price_desc | dud_score | top_rated
    page_size : items per page (capped at ``SEARCH_PAGE_SIZE_MAX``)
    offset    : zero-based offset for pagination
    """

    permission_classes = [AllowAny]
    throttle_classes = [SearchRateThrottle, AnonSearchThrottle, UserSearchThrottle]

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if not query:
            return error_response("validation_error", "?q= is required.")

        category = request.query_params.get("category")
        brand = request.query_params.get("brand")
        sort_by = request.query_params.get("sort_by", "relevance")
        min_price_raw = request.query_params.get("min_price")
        max_price_raw = request.query_params.get("max_price")

        # Validate and parse numeric pagination params.
        max_allowed = SearchConfig.page_size_max()
        default_size = SearchConfig.page_size_default()
        try:
            page_size = min(
                int(request.query_params.get("page_size", default_size)),
                max_allowed,
            )
            offset = max(int(request.query_params.get("offset", "0")), 0)
        except (ValueError, TypeError):
            return error_response(
                "invalid_params", "page_size and offset must be integers."
            )

        # Validate price bounds early so we return a clear error regardless of
        # whether we hit Meilisearch or the DB fallback.
        min_price: Decimal | None = None
        max_price: Decimal | None = None
        if min_price_raw is not None:
            try:
                min_price = Decimal(min_price_raw)
            except (InvalidOperation, ValueError):
                return error_response("invalid_params", "min_price must be a valid number.")
        if max_price_raw is not None:
            try:
                max_price = Decimal(max_price_raw)
            except (InvalidOperation, ValueError):
                return error_response("invalid_params", "max_price must be a valid number.")

        meili_sort_map = SearchConfig.meili_sort_map()
        sort_params = meili_sort_map.get(sort_by, [])

        client = _meilisearch_client()
        if client:
            try:
                filters: list[str] = []
                if category:
                    filters.append(f"category_slug = '{category}'")
                if brand:
                    filters.append(f"brand_slug = '{brand}'")
                if min_price is not None:
                    filters.append(f"current_best_price >= {min_price}")
                if max_price is not None:
                    filters.append(f"current_best_price <= {max_price}")

                params: dict = {"limit": page_size, "offset": offset}
                if filters:
                    params["filter"] = " AND ".join(filters)
                if sort_params:
                    params["sort"] = sort_params

                results = client.index("products").search(query, params)
                return success_response({
                    "results": results.get("hits", []),
                    "total": results.get(
                        "estimatedTotalHits", len(results.get("hits", []))
                    ),
                    "offset": offset,
                    "limit": page_size,
                    "query": query,
                })
            except Exception:
                pass  # fall through to DB fallback

        # ---- DB fallback — simple icontains search ----
        from apps.products.models import Product
        from apps.products.serializers import ProductListSerializer

        # Map public sort_by to ORM ordering (reuse product sort map where possible).
        db_sort_map: dict[str, list[str]] = {
            "relevance": ["-created_at"],
            "price_asc": ["current_best_price"],
            "price_desc": ["-current_best_price"],
            "dud_score": ["-dud_score"],
            "top_rated": ["-avg_rating"],
            "newest": ["-created_at"],
        }
        db_ordering = db_sort_map.get(sort_by, ["-created_at"])

        qs = (
            Product.objects
            .select_related("brand", "category")
            .filter(title__icontains=query, status=Product.Status.ACTIVE)
        )
        if category:
            qs = qs.filter(category__slug=category)
        if brand:
            qs = qs.filter(brand__slug=brand)
        if min_price is not None:
            qs = qs.filter(current_best_price__gte=min_price)
        if max_price is not None:
            qs = qs.filter(current_best_price__lte=max_price)

        qs = qs.order_by(*db_ordering)
        total = qs.count()
        page = qs[offset: offset + page_size]

        return success_response({
            "results": ProductListSerializer(page, many=True).data,
            "total": total,
            "offset": offset,
            "limit": page_size,
            "query": query,
            "source": "db_fallback",
        })


class AutocompleteView(APIView):
    """GET /api/v1/search/autocomplete?q=

    Returns up to ``SEARCH_AUTOCOMPLETE_LIMIT`` lightweight suggestions for
    the type-ahead dropdown.  Minimum query length is ``SEARCH_MIN_QUERY_LENGTH``.
    """

    permission_classes = [AllowAny]
    throttle_classes = [SearchRateThrottle, AnonSearchThrottle, UserSearchThrottle]

    def get(self, request: Request) -> Response:
        query = request.query_params.get("q", "").strip()
        if len(query) < SearchConfig.min_query_length():
            return success_response([])

        limit = SearchConfig.autocomplete_limit()

        client = _meilisearch_client()
        if client:
            try:
                results = client.index("products").search(
                    query,
                    {
                        "limit": limit,
                        "attributesToRetrieve": ["id", "slug", "title", "category_name"],
                    },
                )
                return success_response(results.get("hits", []))
            except Exception:
                pass

        # DB fallback
        from apps.products.models import Product

        hits = list(
            Product.objects
            .filter(title__istartswith=query, status=Product.Status.ACTIVE)
            .values("id", "slug", "title")[:limit]
        )
        for h in hits:
            h["id"] = str(h["id"])
        return success_response(hits)


class AdhocScrapeView(APIView):
    """POST /api/v1/search/adhoc — trigger on-demand scrape for an unknown URL."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        # TODO Sprint 2: validate URL, enqueue scraping Celery task
        return error_response(
            "not_implemented", "On-demand scrape available in Sprint 2.", status=501
        )
