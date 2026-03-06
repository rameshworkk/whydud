"""Django admin for products."""
from django.contrib import admin

from .models import (
    BankCard, Brand, Category, Marketplace, MarketplaceCategoryMapping,
    Product, ProductListing, Seller,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ["title", "brand", "category", "dud_score", "status", "total_reviews", "updated_at"]
    list_filter = ["status", "category", "is_refurbished"]
    search_fields = ["title", "slug", "brand__name"]
    readonly_fields = ["id", "created_at", "updated_at", "first_seen_at"]


@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "scraper_status"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent_display", "level", "slug", "product_count", "is_active", "display_order"]
    list_filter = ["level", "is_active", "parent"]
    list_editable = ["display_order", "is_active"]
    search_fields = ["name", "slug"]
    ordering = ["level", "parent__name", "display_order", "name"]

    @admin.display(description="Hierarchy")
    def parent_display(self, obj):
        parts = []
        current = obj.parent
        while current:
            parts.append(current.name)
            current = current.parent
        return " > ".join(reversed(parts)) if parts else "—"


@admin.register(MarketplaceCategoryMapping)
class MarketplaceCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ["marketplace", "marketplace_category_path", "canonical_category", "confidence", "updated_at"]
    list_filter = ["marketplace", "confidence"]
    search_fields = ["marketplace_category_path", "canonical_category__name"]
    list_editable = ["canonical_category", "confidence"]
    raw_id_fields = ["canonical_category"]
    actions = ["mark_as_reviewed"]

    @admin.action(description="Mark selected mappings as reviewed (manual)")
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(confidence="manual")
        self.message_user(request, f"{updated} mappings marked as reviewed.")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "verified"]
    list_filter = ["verified"]
    search_fields = ["name", "slug"]


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = ["product", "marketplace", "current_price", "in_stock", "last_scraped_at"]
    list_filter = ["marketplace", "in_stock"]
    search_fields = ["product__title", "external_id"]


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ["bank_name", "card_variant", "card_type", "card_network"]
    list_filter = ["bank_slug", "card_type", "card_network"]
