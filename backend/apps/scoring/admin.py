from django.contrib import admin
from .models import DudScoreConfig

@admin.register(DudScoreConfig)
class DudScoreConfigAdmin(admin.ModelAdmin):
    list_display = ["version", "is_active", "activated_at", "change_reason", "created_at"]
    readonly_fields = ["version", "activated_at", "created_at"]
