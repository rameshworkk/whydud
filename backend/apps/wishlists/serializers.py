from rest_framework import serializers
from .models import Wishlist, WishlistItem

class WishlistItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = WishlistItem
        fields = ["id", "product", "price_when_added", "target_price", "alert_enabled",
                  "current_price", "price_change_pct", "notes", "priority", "added_at"]
        read_only_fields = ["id", "price_when_added", "current_price", "price_change_pct", "added_at"]

class WishlistSerializer(serializers.ModelSerializer):
    items = WishlistItemSerializer(many=True, read_only=True)
    class Meta:
        model = Wishlist
        fields = ["id", "name", "is_default", "is_public", "share_slug", "items", "created_at"]
        read_only_fields = ["id", "share_slug", "created_at"]
