"""Serializers for the products app."""
from django.db.models import Avg, Count
from rest_framework import serializers

from .models import BankCard, Brand, Category, Marketplace, Product, ProductListing, Seller


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


class SellerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Seller
        fields = ["id", "name", "avg_rating", "positive_pct", "is_verified"]


class ProductListingSerializer(serializers.ModelSerializer):
    """Marketplace listing row — used inside ProductDetailSerializer."""

    marketplace = MarketplaceSerializer(read_only=True)
    seller = SellerSerializer(read_only=True)
    buy_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductListing
        fields = [
            "id", "marketplace", "seller", "external_url", "buy_url",
            "current_price", "mrp", "discount_pct", "in_stock",
            "rating", "review_count", "last_scraped_at",
        ]

    def get_buy_url(self, obj: ProductListing) -> str:
        """Inject affiliate tag at response time — never stored in DB."""
        if obj.affiliate_url:
            return obj.affiliate_url
        m = obj.marketplace
        if m.affiliate_tag and m.affiliate_param:
            sep = "&" if "?" in obj.external_url else "?"
            return f"{obj.external_url}{sep}{m.affiliate_param}={m.affiliate_tag}"
        return obj.external_url


class ProductListSerializer(serializers.ModelSerializer):
    """Compact, flat serializer for product cards on list/search pages.

    Uses plain string fields (``brand_name``, ``category_name``) instead of
    nested objects to minimise payload size when returning many products.
    The ``images`` field is a JSON array stored on the model; consumers should
    use the first element as the card thumbnail.
    """

    brand_name = serializers.CharField(source="brand.name", default=None, read_only=True)
    brand_slug = serializers.CharField(source="brand.slug", default=None, read_only=True)
    category_name = serializers.CharField(source="category.name", default=None, read_only=True)
    category_slug = serializers.CharField(source="category.slug", default=None, read_only=True)

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title",
            "brand_name", "brand_slug",
            "category_name", "category_slug",
            "current_best_price", "current_best_marketplace",
            "lowest_price_ever",
            "avg_rating", "total_reviews",
            "dud_score", "dud_score_confidence",
            "images",
            "is_refurbished",
            "status",
        ]


class ProductDetailSerializer(serializers.ModelSerializer):
    """Full product detail including listings and aggregated review summary.

    Nested ``brand`` and ``category`` objects are included here (versus the
    flat strings in ``ProductListSerializer``) because the detail page renders
    brand logos, category breadcrumbs, and TCO links.
    """

    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    listings = ProductListingSerializer(many=True, read_only=True)
    review_summary = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = [
            "id", "slug", "title",
            "brand", "category",
            "description", "specs", "images",
            "dud_score", "dud_score_confidence", "dud_score_updated_at",
            "avg_rating", "total_reviews",
            "current_best_price", "current_best_marketplace",
            "lowest_price_ever", "lowest_price_date",
            "status", "is_refurbished",
            "listings",
            "review_summary",
            "first_seen_at", "last_scraped_at",
        ]

    def get_review_summary(self, obj: Product) -> dict:
        """Aggregate review statistics for this product.

        Returns a single dict rather than a full serialised queryset to avoid
        N+1 issues and to keep the detail payload size predictable.
        """
        from apps.reviews.models import Review  # local import avoids circular

        reviews = Review.objects.filter(product=obj)
        total = reviews.count()

        if total == 0:
            return {
                "total_reviews": 0,
                "avg_rating": None,
                "rating_distribution": {str(i): 0 for i in range(1, 6)},
                "verified_purchase_pct": None,
                "avg_credibility_score": None,
                "fraud_flagged_count": 0,
            }

        agg = reviews.aggregate(avg_credibility=Avg("credibility_score"))
        dist_qs = reviews.values("rating").annotate(count=Count("id"))

        distribution: dict[str, int] = {str(i): 0 for i in range(1, 6)}
        for row in dist_qs:
            distribution[str(row["rating"])] = row["count"]

        verified_count = reviews.filter(is_verified_purchase=True).count()
        flagged_count = reviews.filter(is_flagged=True).count()
        avg_credibility = agg["avg_credibility"]

        return {
            "total_reviews": total,
            "avg_rating": float(obj.avg_rating) if obj.avg_rating is not None else None,
            "rating_distribution": distribution,
            "verified_purchase_pct": (
                round(verified_count / total, 4) if total else None
            ),
            "avg_credibility_score": (
                round(float(avg_credibility), 4) if avg_credibility is not None else None
            ),
            "fraud_flagged_count": flagged_count,
        }


class BankCardSerializer(serializers.ModelSerializer):
    class Meta:
        model = BankCard
        fields = [
            "id", "bank_slug", "bank_name", "card_variant", "card_type",
            "card_network", "is_co_branded", "default_cashback_pct", "logo_url",
        ]
