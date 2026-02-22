from django.contrib import admin
from .models import Deal

@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["product", "deal_type", "current_price", "discount_pct", "confidence", "is_active", "detected_at"]
    list_filter = ["deal_type", "confidence", "is_active"]
    search_fields = ["product__title"]
