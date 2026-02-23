"""Product views."""
from decimal import Decimal, InvalidOperation

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import ProductConfig
from common.pagination import CursorPagination, ProductListPagination
from common.rate_limiting import ProductViewThrottle
from common.utils import error_response, success_response

from .models import BankCard, Product
from .serializers import (
    BankCardSerializer,
    ProductDetailSerializer,
    ProductListSerializer,
)


class ProductListView(APIView):
    """GET /api/v1/products/

    Returns a cursor-paginated list of active products.  All filter and sort
    parameters are optional; defaults come from ``ProductConfig`` / settings.

    Query params
    ------------
    category  : category slug — filter to one category
    brand     : brand slug — filter to one brand
    min_price : minimum ``current_best_price`` (in paisa, integer or decimal)
    max_price : maximum ``current_best_price`` (in paisa, integer or decimal)
    sort_by   : one of the keys in ``PRODUCT_SORT_OPTIONS`` setting
    q         : simple title keyword filter (use ``/search`` for full-text)
    status    : product status string (default: active only)
    page_size : items per page (capped at ``PRODUCT_LIST_PAGE_SIZE_MAX``)
    cursor    : opaque cursor token from previous response
    """

    permission_classes = [AllowAny]
    throttle_classes = [ProductViewThrottle]

    def get(self, request: Request) -> Response:
        sort_map = ProductConfig.sort_map()
        sort_by = request.query_params.get("sort_by", "dud_score")

        if sort_by not in sort_map:
            return error_response(
                "invalid_params",
                f"sort_by must be one of: {', '.join(sort_map.keys())}",
            )

        # Non-empty ordering list, or fall back to default field.
        ordering: list[str] = sort_map[sort_by] or [ProductConfig.default_ordering()]
        # Always append UUID tiebreaker for stable cursor pagination when the
        # primary sort field has duplicate values.
        if "id" not in ordering:
            ordering = ordering + ["id"]

        qs = (
            Product.objects
            .select_related("brand", "category")
            .filter(status=Product.Status.ACTIVE)
        )

        # ---- optional filters ----

        if category := request.query_params.get("category"):
            qs = qs.filter(category__slug=category)

        if brand := request.query_params.get("brand"):
            qs = qs.filter(brand__slug=brand)

        if q := request.query_params.get("q"):
            qs = qs.filter(title__icontains=q)

        # status override (e.g. ?status=discontinued for internal tools)
        if status_param := request.query_params.get("status"):
            qs = qs.filter(status=status_param)

        for param_name, lookup in (("min_price", "gte"), ("max_price", "lte")):
            raw = request.query_params.get(param_name)
            if raw is not None:
                try:
                    value = Decimal(raw)
                    qs = qs.filter(**{f"current_best_price__{lookup}": value})
                except (InvalidOperation, ValueError):
                    return error_response(
                        "invalid_params", f"{param_name} must be a valid number."
                    )

        qs = qs.order_by(*ordering)

        paginator = ProductListPagination()
        # Pass the computed ordering so the cursor encodes the correct fields.
        paginator.ordering = ordering
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ProductListSerializer(page, many=True).data
            )
        return success_response(ProductListSerializer(qs, many=True).data)


class ProductDetailView(APIView):
    """GET /api/v1/products/:slug/"""

    permission_classes = [AllowAny]
    throttle_classes = [ProductViewThrottle]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(
            Product.objects
            .select_related("brand", "category")
            .prefetch_related("listings__marketplace", "listings__seller"),
            slug=slug,
        )
        return success_response(
            ProductDetailSerializer(product, context={"request": request}).data
        )


class ProductPriceHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 2 Week 5: query TimescaleDB price_snapshots
        return error_response(
            "not_implemented", "Price history available in Sprint 2.", status=501
        )


class ProductBestDealsView(APIView):
    """Personalized card × marketplace deal optimizer."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 3 Week 9
        return error_response(
            "not_implemented", "Card optimizer available in Sprint 3.", status=501
        )


class ProductTCOView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 4 Week 10
        return error_response(
            "not_implemented", "TCO calculation available in Sprint 4.", status=501
        )


class ProductDiscussionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        from apps.discussions.models import DiscussionThread
        from apps.discussions.serializers import DiscussionThreadSerializer

        product = get_object_or_404(Product, slug=slug)
        qs = (
            DiscussionThread.objects.filter(product=product, is_removed=False)
            .select_related("user")
            .order_by("-is_pinned", "-created_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                DiscussionThreadSerializer(page, many=True, context={"request": request}).data
            )
        return success_response(
            DiscussionThreadSerializer(qs, many=True, context={"request": request}).data
        )

    def post(self, request: Request, slug: str) -> Response:
        from apps.discussions.models import DiscussionThread
        from apps.discussions.serializers import (
            DiscussionThreadCreateSerializer,
            DiscussionThreadSerializer,
        )

        if not request.user or not request.user.is_authenticated:
            return error_response("authentication_required", "Login required to post.", status=401)

        product = get_object_or_404(Product, slug=slug)
        serializer = DiscussionThreadCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        thread = serializer.save(product=product, user=request.user)
        return success_response(
            DiscussionThreadSerializer(thread, context={"request": request}).data, status=201
        )


class CompareView(APIView):
    """GET /api/v1/compare?slugs=slug1,slug2,slug3"""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        slugs_param = request.query_params.get("slugs", "")
        slugs = [s.strip() for s in slugs_param.split(",") if s.strip()]
        if not (2 <= len(slugs) <= 4):
            return error_response(
                "invalid_params", "Provide 2–4 product slugs via ?slugs=.", status=400
            )
        products = list(
            Product.objects.filter(slug__in=slugs)
            .select_related("brand", "category")
            .prefetch_related("listings__marketplace", "listings__seller")
        )
        return success_response(
            ProductDetailSerializer(products, many=True, context={"request": request}).data
        )


class BankListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        banks = (
            BankCard.objects.values("bank_slug", "bank_name", "logo_url")
            .distinct()
            .order_by("bank_name")
        )
        return success_response(list(banks))


class BankCardVariantsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, bank_slug: str) -> Response:
        cards = BankCard.objects.filter(bank_slug=bank_slug).order_by("card_variant")
        if not cards.exists():
            return error_response("not_found", "Bank not found.", status=404)
        return success_response(BankCardSerializer(cards, many=True).data)
