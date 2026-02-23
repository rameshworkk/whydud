"""Serializers for the wishlists app."""
from rest_framework import serializers

from apps.products.serializers import ProductListSerializer
from .models import Wishlist, WishlistItem


class WishlistItemSerializer(serializers.ModelSerializer):
    product = ProductListSerializer(read_only=True)
    product_id = serializers.UUIDField(write_only=True)

    class Meta:
        model = WishlistItem
        fields = [
            "id", "product", "product_id",
            "price_when_added", "target_price",
            "alert_enabled", "last_alerted_at",
            "current_price", "price_change_pct",
            "lowest_since_added", "notes", "priority", "added_at",
        ]
        read_only_fields = [
            "id", "price_when_added", "last_alerted_at",
            "current_price", "price_change_pct", "lowest_since_added", "added_at",
        ]


class WishlistSerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()

    class Meta:
        model = Wishlist
        fields = [
            "id", "name", "is_default", "is_public",
            "share_slug", "item_count", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "is_default", "share_slug", "created_at", "updated_at"]

    def get_item_count(self, obj: Wishlist) -> int:
        return obj.items.count()


class WishlistDetailSerializer(WishlistSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)

    class Meta(WishlistSerializer.Meta):
        fields = WishlistSerializer.Meta.fields + ["items"]
