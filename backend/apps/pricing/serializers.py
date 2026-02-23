"""Serializers for the pricing app."""
from rest_framework import serializers

from .models import MarketplaceOffer, PriceAlert


class MarketplaceOfferSerializer(serializers.ModelSerializer):
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)
    marketplace_slug = serializers.CharField(source="marketplace.slug", read_only=True)

    class Meta:
        model = MarketplaceOffer
        fields = [
            "id", "marketplace_name", "marketplace_slug",
            "scope_type", "offer_type", "title", "description",
            "bank_slug", "card_type", "card_network", "card_variants",
            "wallet_provider", "coupon_code",
            "discount_type", "discount_value", "max_discount", "min_purchase",
            "emi_tenures", "emi_interest_rate", "emi_processing_fee",
            "valid_from", "valid_until", "stackable", "is_active",
            "last_verified_at", "terms_conditions",
        ]


class PriceAlertSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)
    current_best_price = serializers.DecimalField(
        source="product.current_best_price", max_digits=12, decimal_places=2, read_only=True
    )

    class Meta:
        model = PriceAlert
        fields = [
            "id", "product_slug", "product_title",
            "target_price", "current_best_price",
            "is_active", "last_alerted_at", "created_at",
        ]
        read_only_fields = ["id", "last_alerted_at", "created_at"]
