"""Serializers for the products app."""
from rest_framework import serializers

from .models import Brand, BankCard, Category, Marketplace, Product, ProductListing, Seller


class MarketplaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marketplace
        fields = ["id", "slug", "name", "base_url"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name", "level", "has_tco_model", "product_count"]


class BrandSerializer(serializers.ModelSerializer):
    class Meta:
        model = Brand
        fields = ["id", "slug", "name", "logo_url", "verified"]


class ProductListingSerializer(serializers.ModelSerializer):
    marketplace = MarketplaceSerializer(read_only=True)

    class Meta:
        model = ProductListing
        fields = [
            "id", "marketplace", "external_url", "affiliate_url",
            "current_price", "mrp", "discount_pct", "in_stock",
            "rating", "review_count", "last_scraped_at",
        ]


class ProductSerializer(serializers.ModelSerializer):
    """Compact representation for lists/search results."""
    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title", "brand", "category",
            "dud_score", "dud_score_confidence",
            "avg_rating", "total_reviews",
            "current_best_price", "current_best_marketplace",
            "lowest_price_ever", "images",
        ]


class ProductDetailSerializer(ProductSerializer):
    """Full product detail including listings."""
    listings = ProductListingSerializer(many=True, read_only=True)

    class Meta(ProductSerializer.Meta):
        fields = ProductSerializer.Meta.fields + [
            "description", "specs", "listings",
            "dud_score_updated_at", "last_scraped_at",
        ]


class BankCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankCard
        fields = ["id", "bank_slug", "bank_name", "card_variant", "card_type",
                  "card_network", "is_co_branded", "default_cashback_pct", "logo_url"]
