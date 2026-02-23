"""Pricing views — active offers and user price alerts."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import MarketplaceOffer, PriceAlert
from .serializers import MarketplaceOfferSerializer, PriceAlertSerializer


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


class PriceAlertListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        alerts = PriceAlert.objects.filter(user=request.user).select_related("product")
        return success_response(PriceAlertSerializer(alerts, many=True).data)

    def post(self, request: Request) -> Response:
        from apps.products.models import Product

        product_slug = request.data.get("product_slug")
        if not product_slug:
            return error_response("validation_error", "product_slug is required.")

        product = get_object_or_404(Product, slug=product_slug)

        serializer = PriceAlertSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        alert, created = PriceAlert.objects.update_or_create(
            user=request.user,
            product=product,
            defaults={
                "target_price": serializer.validated_data["target_price"],
                "is_active": True,
            },
        )
        code = 201 if created else 200
        return success_response(PriceAlertSerializer(alert).data, status=code)


class PriceAlertDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: str) -> Response:
        alert = PriceAlert.objects.filter(user=request.user, pk=pk).first()
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
