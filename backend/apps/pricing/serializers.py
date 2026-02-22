from rest_framework import serializers
from .models import MarketplaceOffer, PriceAlert

class PricePointSerializer(serializers.Serializer):
    time = serializers.DateTimeField()
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    marketplace_id = serializers.IntegerField()

class MarketplaceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketplaceOffer
        fields = [
            "id", "offer_type", "title", "bank_slug", "card_type",
            "card_variants", "discount_type", "discount_value",
            "max_discount", "min_purchase", "emi_tenures",
            "valid_until", "coupon_code", "last_verified_at",
        ]

class PriceAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriceAlert
        fields = ["id", "product", "target_price", "is_active", "last_alerted_at", "created_at"]
        read_only_fields = ["id", "last_alerted_at", "created_at"]
