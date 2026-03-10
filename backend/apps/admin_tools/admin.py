"""Django Admin registrations for admin_tools models."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .mixins import AuditLogMixin
from .models import AuditLog, ModerationQueue, ScraperRun, SiteConfig


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = [
        "admin_user_email", "action", "target_type", "target_id",
        "changes_preview", "ip_address", "created_at",
    ]
    list_filter = ["action", "target_type", "created_at"]
    search_fields = ["target_type", "target_id", "admin_user__email"]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]
    list_per_page = 50
    readonly_fields = [
        "id", "admin_user", "action", "target_type", "target_id",
        "old_value", "new_value", "ip_address", "created_at",
    ]

    @admin.display(description="Admin", ordering="admin_user__email")
    def admin_user_email(self, obj):
        if obj.admin_user:
            return obj.admin_user.email
        return format_html('<span style="color:#94a3b8;">—</span>')

    @admin.display(description="Changes")
    def changes_preview(self, obj):
        val = obj.new_value or obj.old_value
        if not val:
            return "—"
        text = str(val)
        if len(text) > 60:
            text = text[:60] + "..."
        return text

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
class SiteConfigAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = ["key", "value_preview", "updated_by", "updated_at"]
    list_editable = []  # JSONField can't be list_editable — use detail view
    search_fields = ["key"]
    readonly_fields = ["created_at", "updated_at"]
    list_per_page = 50

    @admin.display(description="Value")
    def value_preview(self, obj):
        text = str(obj.value)
        if len(text) > 50:
            text = text[:50] + "..."
        return text

    def save_model(self, request, obj, form, change) -> None:
        obj.updated_by = request.user
        super().save_model(request, obj, form, change)
