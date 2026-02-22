from django.contrib import admin
from .models import ScraperJob

@admin.register(ScraperJob)
class ScraperJobAdmin(admin.ModelAdmin):
    list_display = ["spider_name", "marketplace", "status", "items_scraped", "items_failed", "started_at"]
    list_filter = ["status", "marketplace", "triggered_by"]
    readonly_fields = ["id", "started_at", "finished_at", "created_at"]
