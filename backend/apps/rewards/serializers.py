"""Serializers for the rewards app."""
from rest_framework import serializers

from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger


class RewardBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardBalance
        fields = ["total_earned", "total_spent", "total_expired", "current_balance", "updated_at"]


class RewardPointsLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardPointsLedger
        fields = [
            "id", "points", "action_type", "reference_type",
            "reference_id", "description", "expires_at", "created_at",
        ]


class GiftCardCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardCatalog
        fields = [
            "id", "brand_name", "brand_slug", "brand_logo_url",
            "denominations", "category", "fulfillment_partner",
        ]


class GiftCardRedemptionSerializer(serializers.ModelSerializer):
    brand_name = serializers.CharField(source="catalog.brand_name", read_only=True)
    brand_logo_url = serializers.URLField(source="catalog.brand_logo_url", read_only=True)

    class Meta:
        model = GiftCardRedemption
        fields = [
            "id", "brand_name", "brand_logo_url",
            "denomination", "points_spent", "status",
            "delivery_email", "fulfilled_at", "created_at",
        ]
        read_only_fields = ["id", "status", "fulfilled_at", "created_at"]


class RedeemGiftCardSerializer(serializers.Serializer):
    catalog_id = serializers.IntegerField()
    denomination = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_email = serializers.EmailField(required=False)
