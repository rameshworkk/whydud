"""Rewards views — points balance, ledger, gift card redemption."""
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import RewardsConfig
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
from .services import deduct_points, get_balance


class RewardBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        balance = get_balance(request.user.pk)
        return success_response(RewardBalanceSerializer(balance).data)


class RewardHistoryView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = RewardPointsLedger.objects.filter(user=request.user).order_by("-created_at")

        # Optional action_type filter
        action_type = request.query_params.get("action_type")
        if action_type:
            qs = qs.filter(action_type=action_type)

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

        # Conversion: points_per_rupee points = ₹1
        points_per_rupee = RewardsConfig.points_per_rupee()
        points_required = int(denomination) * points_per_rupee
        balance = RewardBalance.objects.select_for_update().filter(user=request.user).first()

        if not balance or balance.current_balance < points_required:
            current = balance.current_balance if balance else 0
            return error_response(
                "insufficient_points",
                f"You need {points_required} points but have {current}.",
            )

        # Deduct via service layer
        deduct_points(
            user_id=request.user.pk,
            points=points_required,
            action_type="redemption",
            reference_type="gift_card",
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

        # Queue fulfillment task
        from .tasks import fulfill_gift_card

        fulfill_gift_card.delay(str(redemption.pk))

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
