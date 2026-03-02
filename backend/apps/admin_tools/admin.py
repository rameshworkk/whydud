"""Django Admin registrations for admin_tools models."""
from django.contrib import admin
from django.utils import timezone

from .models import AuditLog, ModerationQueue, ScraperRun, SiteConfig


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["action", "target_type", "target_id", "admin_user", "ip_address", "created_at"]
    list_filter = ["action", "target_type"]
    search_fields = ["target_id", "ip_address"]
    date_hierarchy = "created_at"
    readonly_fields = [
        "id", "admin_user", "action", "target_type", "target_id",
        "old_value", "new_value", "ip_address", "created_at",
    ]

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        return False


@admin.register(ModerationQueue)
class ModerationQueueAdmin(admin.ModelAdmin):
    list_display = ["item_type", "item_id", "reason_short", "status", "assigned_to", "created_at"]
    list_filter = ["status", "item_type"]
    search_fields = ["item_id", "reason"]
    readonly_fields = ["id", "created_at"]
    actions = ["approve_selected", "reject_selected"]

    @admin.display(description="Reason")
    def reason_short(self, obj: ModerationQueue) -> str:
        """Truncated reason for list display."""
        return obj.reason[:80] + "..." if len(obj.reason) > 80 else obj.reason

    @admin.action(description="Approve selected items")
    def approve_selected(self, request, queryset) -> None:
        queryset.filter(status=ModerationQueue.Status.PENDING).update(
            status=ModerationQueue.Status.APPROVED,
            assigned_to=request.user,
            resolved_at=timezone.now(),
        )

    @admin.action(description="Reject selected items")
    def reject_selected(self, request, queryset) -> None:
        queryset.filter(status=ModerationQueue.Status.PENDING).update(
            status=ModerationQueue.Status.REJECTED,
            assigned_to=request.user,
            resolved_at=timezone.now(),
        )


@admin.register(ScraperRun)
class ScraperRunAdmin(admin.ModelAdmin):
    list_display = [
        "spider_name", "marketplace", "status_badge",
        "items_scraped", "items_created", "items_updated",
        "error_count", "started_at", "completed_at",
    ]
    list_filter = ["status", "marketplace"]
    search_fields = ["spider_name"]
    readonly_fields = ["id", "started_at"]

    @admin.display(description="Status")
    def status_badge(self, obj: ScraperRun) -> str:
        """Status with visual indicator for admin list."""
        icons = {
            ScraperRun.Status.RUNNING: "⏳",
            ScraperRun.Status.COMPLETED: "✅",
            ScraperRun.Status.FAILED: "❌",
            ScraperRun.Status.PARTIAL: "⚠️",
        }
        return f"{icons.get(obj.status, '')} {obj.get_status_display()}"


@admin.register(SiteConfig)
class SiteConfigAdmin(admin.ModelAdmin):
    list_display = ["key", "value", "updated_by", "updated_at"]
    search_fields = ["key"]
    readonly_fields = ["created_at"]

    def save_model(self, request, obj, form, change) -> None:
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
