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
        "price_data_points", "created_at",
    ]
    list_filter = ["status", "marketplace_slug"]
    search_fields = ["external_id", "title", "ph_code"]
    readonly_fields = ["id", "created_at", "updated_at"]
