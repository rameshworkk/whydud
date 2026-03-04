"""Product views."""
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Max, Min
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import ProductConfig
from common.pagination import CursorPagination, ProductListPagination
from common.rate_limiting import ProductViewThrottle
from common.utils import error_response, success_response

from .models import BankCard, Category, Product, ProductListing, RecentlyViewed, StockAlert
from .serializers import (
    BankCardSerializer,
    ProductDetailSerializer,
    ProductListingSerializer,
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
        sort_by = request.query_params.get("sort_by", "newest")

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
    """GET /api/v1/compare?slugs=slug1,slug2,slug3

    Returns product details + marketplace×product price matrix + spec diff.
    """

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
        if len(products) < 2:
            return error_response("not_found", "One or more products not found.", status=404)

        product_data = ProductDetailSerializer(
            products, many=True, context={"request": request}
        ).data

        # Build marketplace × product price matrix
        price_matrix = self._build_price_matrix(products)

        # Build spec diff highlighting
        spec_diff = self._build_spec_diff(products)

        return success_response({
            "products": product_data,
            "price_matrix": price_matrix,
            "spec_diff": spec_diff,
        })

    @staticmethod
    def _build_price_matrix(products: list[Product]) -> list[dict]:
        """Row per marketplace, column per product slug → price."""
        marketplace_map: dict[str, dict] = {}
        for product in products:
            for listing in product.listings.all():
                mk = listing.marketplace.slug
                if mk not in marketplace_map:
                    marketplace_map[mk] = {"marketplace": listing.marketplace.name, "marketplace_slug": mk}
                marketplace_map[mk][product.slug] = {
                    "price": str(listing.current_price) if listing.current_price else None,
                    "in_stock": listing.in_stock,
                }
        # Fill None for products missing from a marketplace
        for mk_data in marketplace_map.values():
            for product in products:
                mk_data.setdefault(product.slug, None)
        return list(marketplace_map.values())

    @staticmethod
    def _build_spec_diff(products: list[Product]) -> dict:
        """Returns {spec_key: {slug: value, ...}, ...} with differs flag."""
        all_keys: set[str] = set()
        for p in products:
            if p.specs:
                all_keys.update(p.specs.keys())

        diff: dict[str, dict] = {}
        for key in sorted(all_keys):
            values = {}
            for p in products:
                values[p.slug] = (p.specs or {}).get(key)
            unique_vals = {str(v) for v in values.values() if v is not None}
            diff[key] = {"values": values, "differs": len(unique_vals) > 1}
        return diff


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


# ---------------------------------------------------------------------------
# Cross-Platform Price Comparison / Similar / Share
# ---------------------------------------------------------------------------


class ProductListingsView(APIView):
    """GET /api/v1/products/:slug/listings — all marketplace listings."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        listings = (
            ProductListing.objects.filter(product=product)
            .select_related("marketplace", "seller")
            .order_by("current_price")
        )
        return success_response(ProductListingSerializer(listings, many=True).data)


class BestPriceView(APIView):
    """GET /api/v1/products/:slug/best-price — lowest price with affiliate link."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        listing = (
            ProductListing.objects.filter(product=product, in_stock=True, current_price__isnull=False)
            .select_related("marketplace", "seller")
            .order_by("current_price")
            .first()
        )
        if not listing:
            return error_response("not_found", "No in-stock listings found.", status=404)

        data = ProductListingSerializer(listing).data
        data["product_slug"] = product.slug
        data["product_title"] = product.title
        return success_response(data)


class SimilarProductsView(APIView):
    """GET /api/v1/products/:slug/similar — same category + price range."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        if not product.category or product.current_best_price is None:
            return success_response([])

        price = product.current_best_price
        margin = price * Decimal("0.3")
        qs = (
            Product.objects.filter(
                category=product.category,
                status=Product.Status.ACTIVE,
                current_best_price__gte=price - margin,
                current_best_price__lte=price + margin,
            )
            .exclude(id=product.id)
            .select_related("brand", "category")
            .order_by("-dud_score")[:8]
        )
        return success_response(ProductListSerializer(qs, many=True).data)


class AlternativeProductsView(APIView):
    """GET /api/v1/products/:slug/alternatives — direct competitors."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        if not product.category or product.current_best_price is None:
            return success_response([])

        price = product.current_best_price
        margin = price * Decimal("0.2")
        qs = (
            Product.objects.filter(
                category=product.category,
                status=Product.Status.ACTIVE,
                current_best_price__gte=price - margin,
                current_best_price__lte=price + margin,
            )
            .exclude(id=product.id)
            .exclude(brand=product.brand)
            .select_related("brand", "category")
            .order_by("-dud_score")[:8]
        )
        return success_response(ProductListSerializer(qs, many=True).data)


class ShareProductView(APIView):
    """GET /api/v1/products/:slug/share — OG meta + share URL."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        product = get_object_or_404(Product, slug=slug)
        share_url = f"https://whydud.com/product/{product.slug}"
        image = product.images[0] if product.images else None
        price_str = f"₹{product.current_best_price:,.2f}" if product.current_best_price else None

        return success_response({
            "url": share_url,
            "title": product.title,
            "description": (
                f"{product.title} — DudScore {product.dud_score}/100"
                if product.dud_score
                else product.title
            ),
            "image": image,
            "og": {
                "og:title": product.title,
                "og:description": f"Best price: {price_str}" if price_str else "Check price across marketplaces",
                "og:image": image,
                "og:url": share_url,
                "og:type": "product",
            },
        })


class ShareCompareView(APIView):
    """GET /api/v1/compare/share?slugs=slug1,slug2 — comparison share URL."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        slugs_param = request.query_params.get("slugs", "")
        slugs = [s.strip() for s in slugs_param.split(",") if s.strip()]
        if not (2 <= len(slugs) <= 4):
            return error_response(
                "invalid_params", "Provide 2–4 product slugs via ?slugs=.", status=400
            )

        products = list(Product.objects.filter(slug__in=slugs).only("slug", "title", "images"))
        if len(products) < 2:
            return error_response("not_found", "One or more products not found.", status=404)

        slug_str = ",".join(p.slug for p in products)
        share_url = f"https://whydud.com/compare?slugs={slug_str}"
        titles = " vs ".join(p.title[:50] for p in products)

        return success_response({
            "url": share_url,
            "title": titles,
            "description": f"Compare {len(products)} products on Whydud",
            "og": {
                "og:title": titles,
                "og:description": f"Compare {len(products)} products side-by-side on Whydud",
                "og:url": share_url,
                "og:type": "website",
            },
        })


# ---------------------------------------------------------------------------
# Trending & Analytics
# ---------------------------------------------------------------------------


class TrendingProductsView(APIView):
    """GET /api/v1/trending/products — most viewed this week."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        one_week_ago = timezone.now() - timezone.timedelta(days=7)
        top_product_ids = (
            RecentlyViewed.objects.filter(viewed_at__gte=one_week_ago)
            .values("product_id")
            .annotate(view_count=Count("id"))
            .order_by("-view_count")[:20]
        )
        id_order = {row["product_id"]: row["view_count"] for row in top_product_ids}
        if not id_order:
            return success_response([])

        products = (
            Product.objects.filter(id__in=id_order.keys(), status=Product.Status.ACTIVE)
            .select_related("brand", "category")
        )
        sorted_products = sorted(products, key=lambda p: -id_order.get(p.id, 0))
        return success_response(ProductListSerializer(sorted_products, many=True).data)


class RisingProductsView(APIView):
    """GET /api/v1/trending/rising — biggest DudScore increase in 30 days."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        from apps.scoring.models import DudScoreHistory

        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        # Get earliest and latest score per product in the window
        oldest = (
            DudScoreHistory.objects.filter(time__gte=thirty_days_ago)
            .values("product_id")
            .annotate(oldest_time=Min("time"))
        )
        oldest_map = {row["product_id"]: row["oldest_time"] for row in oldest}
        if not oldest_map:
            return success_response([])

        latest = (
            DudScoreHistory.objects.filter(time__gte=thirty_days_ago)
            .values("product_id")
            .annotate(latest_time=Max("time"))
        )
        latest_map = {row["product_id"]: row["latest_time"] for row in latest}

        # Fetch the actual scores at those timestamps
        improvements: list[tuple] = []
        for pid in oldest_map:
            if pid not in latest_map or oldest_map[pid] == latest_map[pid]:
                continue
            old_record = (
                DudScoreHistory.objects.filter(product_id=pid, time=oldest_map[pid])
                .values_list("score", flat=True)
                .first()
            )
            new_record = (
                DudScoreHistory.objects.filter(product_id=pid, time=latest_map[pid])
                .values_list("score", flat=True)
                .first()
            )
            if old_record is not None and new_record is not None:
                delta = new_record - old_record
                if delta > 0:
                    improvements.append((pid, delta))

        improvements.sort(key=lambda x: -x[1])
        top_ids = [pid for pid, _ in improvements[:20]]
        if not top_ids:
            return success_response([])

        products = (
            Product.objects.filter(id__in=top_ids, status=Product.Status.ACTIVE)
            .select_related("brand", "category")
        )
        id_rank = {pid: i for i, pid in enumerate(top_ids)}
        sorted_products = sorted(products, key=lambda p: id_rank.get(p.id, 999))
        return success_response(ProductListSerializer(sorted_products, many=True).data)


class PriceDroppingView(APIView):
    """GET /api/v1/trending/price-dropping — consistent downward price trend."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        from apps.pricing.models import PriceSnapshot

        thirty_days_ago = timezone.now() - timezone.timedelta(days=30)

        # Products where earliest price in window > latest price
        oldest = (
            PriceSnapshot.objects.filter(time__gte=thirty_days_ago)
            .values("product_id")
            .annotate(oldest_time=Min("time"))
        )
        oldest_map = {row["product_id"]: row["oldest_time"] for row in oldest}
        if not oldest_map:
            return success_response([])

        latest = (
            PriceSnapshot.objects.filter(time__gte=thirty_days_ago)
            .values("product_id")
            .annotate(latest_time=Max("time"))
        )
        latest_map = {row["product_id"]: row["latest_time"] for row in latest}

        drops: list[tuple] = []
        for pid in oldest_map:
            if pid not in latest_map or oldest_map[pid] == latest_map[pid]:
                continue
            old_price = (
                PriceSnapshot.objects.filter(product_id=pid, time=oldest_map[pid])
                .values_list("price", flat=True)
                .first()
            )
            new_price = (
                PriceSnapshot.objects.filter(product_id=pid, time=latest_map[pid])
                .values_list("price", flat=True)
                .first()
            )
            if old_price is not None and new_price is not None and new_price < old_price:
                drops.append((pid, old_price - new_price))

        drops.sort(key=lambda x: -x[1])
        top_ids = [pid for pid, _ in drops[:20]]
        if not top_ids:
            return success_response([])

        products = (
            Product.objects.filter(id__in=top_ids, status=Product.Status.ACTIVE)
            .select_related("brand", "category")
        )
        id_rank = {pid: i for i, pid in enumerate(top_ids)}
        sorted_products = sorted(products, key=lambda p: id_rank.get(p.id, 999))
        return success_response(ProductListSerializer(sorted_products, many=True).data)


class CategoryLeaderboardView(APIView):
    """GET /api/v1/categories/:slug/leaderboard — top 10 by DudScore."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        products = (
            Product.objects.filter(
                category=category,
                status=Product.Status.ACTIVE,
                dud_score__isnull=False,
            )
            .select_related("brand", "category")
            .order_by("-dud_score")[:10]
        )
        return success_response(ProductListSerializer(products, many=True).data)


class MostLovedView(APIView):
    """GET /api/v1/categories/:slug/most-loved — highest DudScore."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        products = (
            Product.objects.filter(
                category=category,
                status=Product.Status.ACTIVE,
                dud_score__isnull=False,
            )
            .select_related("brand", "category")
            .order_by("-dud_score")
        )
        paginator = CursorPagination()
        paginator.ordering = ["-dud_score", "id"]
        page = paginator.paginate_queryset(products, request)
        if page is not None:
            return paginator.get_paginated_response(
                ProductListSerializer(page, many=True).data
            )
        return success_response(ProductListSerializer(products, many=True).data)


class MostHatedView(APIView):
    """GET /api/v1/categories/:slug/most-hated — lowest DudScore."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        category = get_object_or_404(Category, slug=slug)
        products = (
            Product.objects.filter(
                category=category,
                status=Product.Status.ACTIVE,
                dud_score__isnull=False,
            )
            .select_related("brand", "category")
            .order_by("dud_score")
        )
        paginator = CursorPagination()
        paginator.ordering = ["dud_score", "id"]
        page = paginator.paginate_queryset(products, request)
        if page is not None:
            return paginator.get_paginated_response(
                ProductListSerializer(page, many=True).data
            )
        return success_response(ProductListSerializer(products, many=True).data)


# ---------------------------------------------------------------------------
# Recently Viewed & Stock Alerts
# ---------------------------------------------------------------------------


class RecentlyViewedView(APIView):
    """GET + POST /api/v1/me/recently-viewed."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """Last 20 products viewed."""
        entries = (
            RecentlyViewed.objects.filter(user=request.user)
            .select_related("product__brand", "product__category")
            .order_by("-viewed_at")[:20]
        )
        products = [e.product for e in entries]
        return success_response(ProductListSerializer(products, many=True).data)

    def post(self, request: Request) -> Response:
        """Log a product view."""
        product_slug = request.data.get("product_slug")
        if not product_slug:
            return error_response("validation_error", "product_slug is required.")

        product = get_object_or_404(Product, slug=product_slug)
        RecentlyViewed.objects.create(user=request.user, product=product)
        return success_response({"detail": "View logged."}, status=201)


class StockAlertListCreateView(APIView):
    """GET + POST /api/v1/alerts/stock."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        """List active stock alerts."""
        alerts = (
            StockAlert.objects.filter(user=request.user, is_active=True)
            .select_related("product__brand", "product__category", "listing__marketplace")
            .order_by("-created_at")
        )
        data = [
            {
                "id": str(a.id),
                "product_slug": a.product.slug,
                "product_title": a.product.title,
                "listing_id": str(a.listing_id) if a.listing_id else None,
                "marketplace": a.listing.marketplace.name if a.listing else None,
                "is_active": a.is_active,
                "created_at": a.created_at.isoformat(),
            }
            for a in alerts
        ]
        return success_response(data)

    def post(self, request: Request) -> Response:
        product_slug = request.data.get("product_slug")
        if not product_slug:
            return error_response("validation_error", "product_slug is required.")

        product = get_object_or_404(Product, slug=product_slug)

        listing = None
        listing_id = request.data.get("listing_id")
        if listing_id:
            listing = get_object_or_404(ProductListing, pk=listing_id, product=product)

        alert, created = StockAlert.objects.get_or_create(
            user=request.user,
            product=product,
            listing=listing,
            defaults={"is_active": True},
        )
        if not created and not alert.is_active:
            alert.is_active = True
            alert.notified_at = None
            alert.save(update_fields=["is_active", "notified_at"])

        return success_response(
            {
                "id": str(alert.id),
                "product_slug": product.slug,
                "listing_id": str(listing.id) if listing else None,
                "is_active": alert.is_active,
                "created_at": alert.created_at.isoformat(),
            },
            status=201 if created else 200,
        )


class DeleteStockAlertView(APIView):
    """DELETE /api/v1/alerts/stock/:id — remove stock alert."""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, pk: str) -> Response:
        alert = StockAlert.objects.filter(user=request.user, pk=pk).first()
        if not alert:
            return error_response("not_found", "Stock alert not found.", status=404)
        alert.delete()
        return success_response({"detail": "Stock alert removed."})
