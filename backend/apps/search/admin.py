from django.contrib import admin
from .models import SearchLog

@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ["query", "results_count", "latency_ms", "created_at"]
    readonly_fields = ["query", "results_count", "latency_ms", "filters_used", "created_at"]
