from django.contrib import admin

from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger


@admin.register(RewardPointsLedger)
class RewardPointsLedgerAdmin(admin.ModelAdmin):
    list_display = ["user", "points", "action_type", "reference_type", "created_at", "expires_at"]
    list_filter = ["action_type"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]


@admin.register(RewardBalance)
class RewardBalanceAdmin(admin.ModelAdmin):
    list_display = ["user", "total_earned", "total_spent", "total_expired", "current_balance", "updated_at"]
    search_fields = ["user__email"]
    readonly_fields = ["updated_at"]


@admin.register(GiftCardCatalog)
class GiftCardCatalogAdmin(admin.ModelAdmin):
    list_display = ["brand_name", "brand_slug", "is_active", "category"]
    list_filter = ["is_active", "category"]


@admin.register(GiftCardRedemption)
class GiftCardRedemptionAdmin(admin.ModelAdmin):
    list_display = ["user", "catalog", "denomination", "points_spent", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "fulfilled_at"]
