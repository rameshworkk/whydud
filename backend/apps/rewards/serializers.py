from rest_framework import serializers
from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger

class RewardBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardBalance
        fields = ["total_earned", "total_spent", "total_expired", "current_balance", "updated_at"]

class RewardPointsLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = RewardPointsLedger
        fields = ["id", "points", "action_type", "description", "expires_at", "created_at"]

class GiftCardCatalogSerializer(serializers.ModelSerializer):
    class Meta:
        model = GiftCardCatalog
        fields = ["id", "brand_name", "brand_slug", "brand_logo_url", "denominations", "category"]

class RedeemSerializer(serializers.Serializer):
    catalog_id = serializers.IntegerField()
    denomination = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_email = serializers.EmailField(required=False)
