"""Django admin for products."""
from django.contrib import admin

from .models import BankCard, Brand, Category, Marketplace, Product, ProductListing, Seller


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
    list_display = ["name", "slug", "level", "has_tco_model", "product_count"]
    list_filter = ["level", "has_tco_model"]


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
