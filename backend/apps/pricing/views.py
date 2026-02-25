"""Pricing views — active offers, user price alerts, and click tracking."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .click_tracking import (
    detect_device_type,
    generate_affiliate_url,
    hash_ip,
    hash_user_agent,
)
from .models import ClickEvent, MarketplaceOffer, PriceAlert
from .serializers import (
    ClickEventSerializer,
    MarketplaceOfferSerializer,
    PriceAlertSerializer,
    TrackClickSerializer,
)


class OffersActiveView(APIView):
    """GET /api/v1/offers/active — list currently active bank/card offers."""
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        qs = MarketplaceOffer.objects.filter(is_active=True).select_related("marketplace")

        marketplace = request.query_params.get("marketplace")
        bank = request.query_params.get("bank")
        offer_type = request.query_params.get("type")

        if marketplace:
            qs = qs.filter(marketplace__slug=marketplace)
        if bank:
            qs = qs.filter(bank_slug=bank)
        if offer_type:
            qs = qs.filter(offer_type=offer_type)

        qs = qs.order_by("-last_verified_at", "-created_at")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                MarketplaceOfferSerializer(page, many=True).data
            )
        return success_response(MarketplaceOfferSerializer(qs, many=True).data)


class EffectivePriceView(APIView):
    """Calculate personalized effective price given user's payment methods."""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, product_slug: str) -> Response:
        # TODO Sprint 3 Week 9: match user's cards vs active offers
        return error_response("not_implemented", "Card optimizer available in Sprint 3.", status=501)


class ListAlertsView(APIView):
    """GET /api/v1/alerts — user's active alerts."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            PriceAlert.objects.filter(user=request.user)
            .select_related("product", "marketplace")
            .order_by("-created_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                PriceAlertSerializer(page, many=True).data
            )
        return success_response(PriceAlertSerializer(qs, many=True).data)


class CreatePriceAlertView(APIView):
    """POST /api/v1/alerts/price — set a price alert."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        from apps.products.models import Marketplace, Product

        product_slug = request.data.get("product_slug")
        if not product_slug:
            return error_response("validation_error", "product_slug is required.")

        product = get_object_or_404(Product, slug=product_slug)

        marketplace = None
        marketplace_slug = request.data.get("marketplace")
        if marketplace_slug:
            marketplace = get_object_or_404(Marketplace, slug=marketplace_slug)

        serializer = PriceAlertSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        alert, created = PriceAlert.objects.update_or_create(
            user=request.user,
            product=product,
            marketplace=marketplace,
            defaults={
                "target_price": serializer.validated_data["target_price"],
                "is_active": True,
            },
        )
        code = 201 if created else 200
        return success_response(PriceAlertSerializer(alert).data, status=code)


class AlertDetailView(APIView):
    """PATCH / DELETE /api/v1/alerts/:id."""

    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: str) -> Response:
        alert = (
            PriceAlert.objects.filter(user=request.user, pk=pk)
            .select_related("product", "marketplace")
            .first()
        )
        if not alert:
            return error_response("not_found", "Price alert not found.", status=404)
        serializer = PriceAlertSerializer(alert, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, pk: str) -> Response:
        alert = PriceAlert.objects.filter(user=request.user, pk=pk).first()
        if not alert:
            return error_response("not_found", "Price alert not found.", status=404)
        alert.delete()
        return success_response({"detail": "Alert deleted."})


class TriggeredAlertsView(APIView):
    """GET /api/v1/alerts/triggered — recently triggered price drops."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            PriceAlert.objects.filter(user=request.user, is_triggered=True)
            .select_related("product", "marketplace")
            .order_by("-triggered_at")
        )
        paginator = CursorPagination()
        paginator.ordering = "-triggered_at"
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                PriceAlertSerializer(page, many=True).data
            )
        return success_response(PriceAlertSerializer(qs, many=True).data)


class TrackClickView(APIView):
    """POST /api/v1/clicks/track — log affiliate click, return redirect URL.

    Accepts authenticated and anonymous users. Anonymous clicks have user=None.
    """

    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        from apps.products.models import ProductListing

        serializer = TrackClickSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        listing_id = serializer.validated_data["listing_id"]
        referrer_page = serializer.validated_data["referrer_page"]
        source_section = serializer.validated_data.get("source_section", "")

        listing = (
            ProductListing.objects.filter(pk=listing_id)
            .select_related("marketplace", "product")
            .first()
        )
        if not listing:
            return error_response("not_found", "Listing not found.", status=404)

        user = request.user if request.user.is_authenticated else None

        # Generate the tracked affiliate URL
        affiliate_url = generate_affiliate_url(listing, user, referrer_page)

        # Extract request metadata
        user_agent = request.META.get("HTTP_USER_AGENT", "")
        ip = request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
        if not ip:
            ip = request.META.get("REMOTE_ADDR", "")

        # Create click event record
        click = ClickEvent.objects.create(
            user=user,
            product=listing.product,
            listing=listing,
            marketplace=listing.marketplace,
            source_page=referrer_page,
            source_section=source_section,
            affiliate_url=affiliate_url,
            affiliate_tag=listing.marketplace.affiliate_tag or "",
            sub_tag=f"{referrer_page}_{source_section}" if source_section else referrer_page,
            price_at_click=listing.current_price,
            device_type=detect_device_type(user_agent) if user_agent else "",
            ip_hash=hash_ip(ip) if ip else "",
            user_agent_hash=hash_user_agent(user_agent) if user_agent else "",
        )

        return success_response(
            {"affiliate_url": affiliate_url, "click_id": click.id},
            status=201,
        )


class ClickHistoryView(APIView):
    """GET /api/v1/clicks/history — user's click history (transparency)."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            ClickEvent.objects.filter(user=request.user)
            .select_related("product", "marketplace")
            .order_by("-clicked_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ClickEventSerializer(page, many=True).data
            )
        return success_response(ClickEventSerializer(qs, many=True).data)
