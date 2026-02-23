"""Rewards views — points balance, ledger, gift card redemption."""
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger
from .serializers import (
    GiftCardCatalogSerializer,
    GiftCardRedemptionSerializer,
    RedeemGiftCardSerializer,
    RewardBalanceSerializer,
    RewardPointsLedgerSerializer,
)


class RewardBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        balance, _ = RewardBalance.objects.get_or_create(user=request.user)
        return success_response(RewardBalanceSerializer(balance).data)


class RewardHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = RewardPointsLedger.objects.filter(user=request.user).order_by("-created_at")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                RewardPointsLedgerSerializer(page, many=True).data
            )
        return success_response(RewardPointsLedgerSerializer(qs, many=True).data)


class GiftCardCatalogView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = GiftCardCatalog.objects.filter(is_active=True).order_by("brand_name")
        category = request.query_params.get("category")
        if category:
            qs = qs.filter(category=category)
        return success_response(GiftCardCatalogSerializer(qs, many=True).data)


class RedeemView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request) -> Response:
        serializer = RedeemGiftCardSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        catalog_id = serializer.validated_data["catalog_id"]
        denomination = serializer.validated_data["denomination"]
        delivery_email = serializer.validated_data.get("delivery_email", request.user.email)

        catalog = GiftCardCatalog.objects.filter(pk=catalog_id, is_active=True).first()
        if not catalog:
            return error_response("not_found", "Gift card catalog item not found.", status=404)

        if denomination not in [d for d in catalog.denominations]:
            return error_response("invalid_denomination", "This denomination is not available.")

        # 1 point = ₹1 conversion (100 paisa); denomination is in rupees
        points_required = int(denomination)
        balance, _ = RewardBalance.objects.select_for_update().get_or_create(user=request.user)

        if balance.current_balance < points_required:
            return error_response(
                "insufficient_points",
                f"You need {points_required} points but have {balance.current_balance}.",
            )

        # Deduct points
        balance.current_balance -= points_required
        balance.total_spent += points_required
        balance.save(update_fields=["current_balance", "total_spent", "updated_at"])

        # Record ledger entry
        RewardPointsLedger.objects.create(
            user=request.user,
            points=-points_required,
            action_type="redemption",
            description=f"Redeemed {catalog.brand_name} ₹{denomination} gift card",
        )

        # Create redemption record
        redemption = GiftCardRedemption.objects.create(
            user=request.user,
            catalog=catalog,
            denomination=denomination,
            points_spent=points_required,
            delivery_email=delivery_email,
            status=GiftCardRedemption.Status.PENDING,
        )

        # TODO Sprint 4: trigger fulfillment Celery task

        return success_response(GiftCardRedemptionSerializer(redemption).data, status=201)


class RedemptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = GiftCardRedemption.objects.filter(user=request.user).select_related("catalog")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                GiftCardRedemptionSerializer(page, many=True).data
            )
        return success_response(GiftCardRedemptionSerializer(qs, many=True).data)
