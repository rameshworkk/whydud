"""Serializers for the deals app."""
from rest_framework import serializers

from apps.products.serializers import ProductListSerializer
from .models import Deal


class DealSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)
    marketplace_slug = serializers.CharField(source="marketplace.slug", read_only=True)
    discount_pct_display = serializers.SerializerMethodField()

    class Meta:
        model = Deal
        fields = [
            "id", "product", "marketplace_name", "marketplace_slug",
            "deal_type", "current_price", "reference_price",
            "discount_pct", "discount_pct_display", "confidence",
            "is_active", "detected_at", "expires_at", "views", "clicks",
        ]

    def get_discount_pct_display(self, obj: Deal) -> str | None:
        if obj.discount_pct:
            return f"{obj.discount_pct:.0f}% off"
        return None
