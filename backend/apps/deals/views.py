"""Deals views."""
from django.shortcuts import get_object_or_404
from django.db.models import F
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import Deal
from .serializers import DealSerializer


class DealListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        qs = Deal.objects.filter(is_active=True).select_related(
            "product__brand", "product__category", "marketplace"
        )

        deal_type = request.query_params.get("type")
        confidence = request.query_params.get("confidence")
        category = request.query_params.get("category")

        if deal_type:
            qs = qs.filter(deal_type=deal_type)
        if confidence:
            qs = qs.filter(confidence=confidence)
        if category:
            qs = qs.filter(product__category__slug=category)

        paginator = CursorPagination()
        paginator.ordering = "-detected_at"
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(DealSerializer(page, many=True).data)
        return success_response(DealSerializer(qs, many=True).data)


class DealDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        deal = get_object_or_404(
            Deal.objects.select_related("product__brand", "product__category", "marketplace"),
            pk=pk,
        )
        # Track view
        Deal.objects.filter(pk=pk).update(views=F("views") + 1)
        return success_response(DealSerializer(deal).data)


class DealClickView(APIView):
    """Record an affiliate click and redirect."""
    permission_classes = [AllowAny]

    def post(self, request: Request, pk: str) -> Response:
        deal = get_object_or_404(Deal, pk=pk, is_active=True)
        Deal.objects.filter(pk=pk).update(clicks=F("clicks") + 1)
        # TODO Sprint 4: return affiliate URL from listing
        return success_response({"deal_id": str(deal.pk), "clicks_recorded": True})
