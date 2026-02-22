from django.contrib import admin
from .models import MarketplaceOffer, PriceAlert

@admin.register(MarketplaceOffer)
class MarketplaceOfferAdmin(admin.ModelAdmin):
    list_display = ["title", "marketplace", "offer_type", "bank_slug", "is_active", "valid_until"]
    list_filter = ["is_active", "offer_type", "marketplace"]
    search_fields = ["title", "bank_slug"]

@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = ["user", "product", "target_price", "is_active"]
