"""Serializers for the products app."""
from django.db.models import Avg, Count
from rest_framework import serializers

from .models import BankCard, Brand, Category, Marketplace, Product, ProductListing, Seller


class MarketplaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Marketplace
        fields = ["id", "slug", "name", "base_url"]


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()
    children_count = serializers.SerializerMethodField()
    breadcrumb = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            "id", "slug", "name", "level", "icon", "description",
            "parent", "product_count", "children_count", "breadcrumb", "has_tco_model",
        ]

    def get_parent(self, obj):
        if obj.parent:
            return {"id": obj.parent.id, "slug": obj.parent.slug, "name": obj.parent.name}
        return None

    def get_children_count(self, obj):
        return obj.children.filter(is_active=True).count() if hasattr(obj, "children") else 0

    def get_breadcrumb(self, obj):
        """Returns [{'slug': 'electronics', 'name': 'Electronics'}, ...] for hierarchy."""
        parts = []
        current = obj
        while current:
            parts.append({"slug": current.slug, "name": current.name})
            current = current.parent
        return list(reversed(parts))


# ---------------------------------------------------------------------------
# Category tree serializers (for mega-nav / browse page)
# ---------------------------------------------------------------------------

class SubcategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "slug", "name", "icon", "product_count"]


class CategoryWithChildrenSerializer(serializers.ModelSerializer):
    subcategories = SubcategorySerializer(source="children", many=True)

    class Meta:
        model = Category
        fields = ["id", "slug", "name", "icon", "product_count", "subcategories"]


class DepartmentTreeSerializer(serializers.ModelSerializer):
    categories = CategoryWithChildrenSerializer(source="children", many=True)

    class Meta:
        model = Category
        fields = ["id", "slug", "name", "icon", "product_count", "categories"]


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

    Pass ``preferred_marketplace_ids`` (list[int]) in serializer context to
    filter listings to only those marketplaces. When the list is non-empty,
    ``filtered_best_price`` is recalculated from the filtered set and
    ``marketplace_filter_active`` is True.
    """

    brand = BrandSerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    listings = serializers.SerializerMethodField()
    review_summary = serializers.SerializerMethodField()
    filtered_best_price = serializers.SerializerMethodField()
    marketplace_filter_active = serializers.SerializerMethodField()

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
            "filtered_best_price", "marketplace_filter_active",
            "first_seen_at", "last_scraped_at",
        ]

    def _get_preferred_ids(self) -> list[int]:
        return self.context.get("preferred_marketplace_ids") or []

    def get_listings(self, obj: Product) -> list[dict]:
        preferred = self._get_preferred_ids()
        qs = obj.listings.all()
        if preferred:
            qs = qs.filter(marketplace_id__in=preferred)
        return ProductListingSerializer(qs, many=True).data

    def get_filtered_best_price(self, obj: Product) -> str | None:
        preferred = self._get_preferred_ids()
        if not preferred:
            return None
        prices = [
            listing.current_price
            for listing in obj.listings.all()
            if listing.marketplace_id in preferred
            and listing.current_price is not None
            and listing.in_stock
        ]
        return str(min(prices)) if prices else None

    def get_marketplace_filter_active(self, obj: Product) -> bool:
        return bool(self._get_preferred_ids())

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
