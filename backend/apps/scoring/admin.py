from django.contrib import admin
from .models import BrandTrustScore, DudScoreConfig

@admin.register(DudScoreConfig)
class DudScoreConfigAdmin(admin.ModelAdmin):
    list_display = ["version", "is_active", "activated_at", "change_reason", "created_at"]
    readonly_fields = ["version", "activated_at", "created_at"]


@admin.register(BrandTrustScore)
class BrandTrustScoreAdmin(admin.ModelAdmin):
    list_display = ["brand", "avg_dud_score", "product_count", "trust_tier", "computed_at"]
    list_filter = ["trust_tier"]
    search_fields = ["brand__name", "brand__slug"]
    readonly_fields = ["computed_at", "created_at", "updated_at"]
