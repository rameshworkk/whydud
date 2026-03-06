from django.contrib import admin
from .models import BackfillProduct, MarketplaceOffer, PriceAlert


@admin.register(MarketplaceOffer)
class MarketplaceOfferAdmin(admin.ModelAdmin):
    list_display = ["title", "marketplace", "offer_type", "bank_slug", "is_active", "valid_until"]
    list_filter = ["is_active", "offer_type", "marketplace"]
    search_fields = ["title", "bank_slug"]


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "target_price", "is_active"]


@admin.register(BackfillProduct)
class BackfillProductAdmin(admin.ModelAdmin):
    list_display = [
        "external_id", "marketplace_slug", "title", "status",
        "scrape_status", "price_data_points", "cached_points", "created_at",
    ]
    list_filter = ["status", "scrape_status", "marketplace_slug"]
    search_fields = ["external_id", "title", "ph_code"]
    readonly_fields = ["id", "created_at", "updated_at", "cached_points", "raw_price_data"]

    @admin.display(description="Cached Pts")
    def cached_points(self, obj):
        return len(obj.raw_price_data) if obj.raw_price_data else 0
