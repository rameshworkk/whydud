from rest_framework import serializers
from .models import Deal

class DealSerializer(serializers.ModelSerializer):
    product_title = serializers.CharField(source="product.title", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    marketplace_name = serializers.CharField(source="marketplace.name", read_only=True)

    class Meta:
        model = Deal
        fields = [
            "id", "product_title", "product_slug", "marketplace_name",
            "deal_type", "current_price", "reference_price", "discount_pct",
            "confidence", "detected_at", "expires_at", "views", "clicks",
        ]
