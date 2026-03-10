"""Reusable admin mixins for audit logging."""


class AuditLogMixin:
    """Auto-logs all admin create/update/delete actions to AuditLog."""

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        try:
            from apps.admin_tools.models import AuditLog

            AuditLog.objects.create(
                admin_user=request.user,
                action=AuditLog.Action.UPDATE if change else AuditLog.Action.CREATE,
                target_type=f"{obj._meta.app_label}.{obj.__class__.__name__}",
                target_id=str(obj.pk),
                new_value={"changed_fields": form.changed_data} if change else {"action": "created"},
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass

    def delete_model(self, request, obj):
        try:
            from apps.admin_tools.models import AuditLog

            AuditLog.objects.create(
                admin_user=request.user,
                action=AuditLog.Action.DELETE,
                target_type=f"{obj._meta.app_label}.{obj.__class__.__name__}",
                target_id=str(obj.pk),
                ip_address=request.META.get("REMOTE_ADDR"),
            )
        except Exception:
            pass
        super().delete_model(request, obj)
