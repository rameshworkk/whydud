from django.contrib import admin
from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger

@admin.register(GiftCardCatalog)
class GiftCardCatalogAdmin(admin.ModelAdmin):
    list_display = ["brand_name", "brand_slug", "is_active", "category"]

@admin.register(GiftCardRedemption)
class GiftCardRedemptionAdmin(admin.ModelAdmin):
    list_display = ["user", "catalog", "denomination", "status", "created_at"]
    list_filter = ["status"]
