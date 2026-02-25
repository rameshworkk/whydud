"""Serializers for the pricing app."""
from rest_framework import serializers

from common.app_settings import ClickTrackingConfig

from .models import ClickEvent, MarketplaceOffer, PriceAlert


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


class TrackClickSerializer(serializers.Serializer):
    """Validates the POST /api/v1/clicks/track request body."""

    listing_id = serializers.UUIDField()
    referrer_page = serializers.ChoiceField(
        choices=[(p, p) for p in ClickTrackingConfig.valid_source_pages()],
        default="product_page",
    )
    source_section = serializers.CharField(max_length=50, required=False, default="")


class ClickEventSerializer(serializers.ModelSerializer):
    """Read-only serializer for click history."""

    product_slug = serializers.CharField(source="product.slug", read_only=True)
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)
    marketplace_slug = serializers.CharField(source="marketplace.slug", read_only=True)

    class Meta:
        model = ClickEvent
        fields = [
            "id", "product_slug", "marketplace_name", "marketplace_slug",
            "source_page", "affiliate_url", "price_at_click", "clicked_at",
        ]
        read_only_fields = fields


class PriceAlertSerializer(serializers.ModelSerializer):
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_title = serializers.CharField(source="product.title", read_only=True)
    marketplace_slug = serializers.CharField(
        source="marketplace.slug", read_only=True, default=None
    )

    class Meta:
        model = PriceAlert
        fields = [
            "id", "product_slug", "product_title",
            "marketplace_slug", "target_price",
            "is_active", "is_triggered",
            "triggered_at", "triggered_price", "triggered_marketplace",
            "created_at",
        ]
        read_only_fields = [
            "id", "is_triggered", "triggered_at",
            "triggered_price", "triggered_marketplace", "created_at",
        ]
