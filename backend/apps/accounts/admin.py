"""Enhanced user admin — stats header, annotations, inlines, management actions."""
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from .models import (
    Notification, NotificationPreference, OAuthConnection,
    PaymentMethod, ReservedUsername, User, WhydudEmail,
)


# ------------------------------------------------------------------
# Inlines
# ------------------------------------------------------------------

class WhydudEmailInline(admin.StackedInline):
    model = WhydudEmail
    extra = 0
    fields = [
        "username", "domain", "is_active",
        "total_emails_received", "total_orders_detected",
        "last_email_received_at", "onboarding_complete",
        "marketplaces_registered",
    ]
    readonly_fields = [
        "total_emails_received", "total_orders_detected",
        "last_email_received_at",
    ]


class NotificationPreferenceInline(admin.StackedInline):
    model = NotificationPreference
    extra = 0
    fields = [
        "price_drops", "return_windows", "refund_delays",
        "back_in_stock", "review_upvotes", "price_alerts",
        "discussion_replies", "level_up", "points_earned",
    ]


# ------------------------------------------------------------------
# UserAdmin
# ------------------------------------------------------------------

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    change_list_template = "admin/accounts/user/change_list.html"

    list_display = [
        "email",
        "name",
        "is_active_icon",
        "role",
        "subscription_tier",
        "review_count",
        "whydud_email_icon",
        "last_login_at",
        "created_at",
    ]
    list_filter = [
        "is_active",
        "is_staff",
        "is_suspended",
        "role",
        "subscription_tier",
        "has_whydud_email",
        "created_at",
        "last_login_at",
    ]
    search_fields = ["email", "name"]
    ordering = ["-created_at"]
    list_per_page = 50
    list_select_related = []
    inlines = [WhydudEmailInline, NotificationPreferenceInline]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal", {"fields": ("name", "avatar_url")}),
        ("Status", {"fields": (
            "role", "subscription_tier", "subscription_expires_at",
            "has_whydud_email", "trust_score", "is_suspended",
        )}),
        ("Permissions", {"fields": (
            "is_active", "is_staff", "is_superuser", "groups", "user_permissions",
        )}),
        ("Timestamps", {"fields": ("last_login_at", "created_at", "updated_at")}),
    )
    readonly_fields = ["created_at", "updated_at", "last_login_at"]
    add_fieldsets = (
        (None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),
    )

    actions = [
        "suspend_users",
        "restore_users",
        "force_password_reset",
        "grant_reward_points",
        "broadcast_notification",
    ]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _review_count=Count("reviews"),
        )

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------

    @admin.display(description="Active", boolean=True, ordering="is_active")
    def is_active_icon(self, obj):
        return obj.is_active

    @admin.display(description="Reviews", ordering="_review_count")
    def review_count(self, obj):
        count = obj._review_count
        if count == 0:
            return format_html('<span style="color:#94a3b8;">0</span>')
        return count

    @admin.display(description="@whyd.*", boolean=True, ordering="has_whydud_email")
    def whydud_email_icon(self, obj):
        return obj.has_whydud_email

    # ------------------------------------------------------------------
    # Admin actions
    # ------------------------------------------------------------------

    @admin.action(description="Suspend selected users (deactivate + hide reviews)")
    def suspend_users(self, request, queryset):
        from apps.reviews.models import Review

        user_ids = list(queryset.values_list("id", flat=True))
        suspended = queryset.update(is_suspended=True, is_active=False)
        hidden = Review.objects.filter(user_id__in=user_ids).update(is_published=False)

        # Audit log
        try:
            from apps.admin_tools.models import AuditLog
            for uid in user_ids:
                AuditLog.objects.create(
                    admin_user=request.user,
                    action=AuditLog.Action.SUSPEND,
                    target_type="accounts.User",
                    target_id=str(uid),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
        except Exception:
            pass

        messages.success(
            request,
            f"Suspended {suspended} users, hid {hidden} reviews.",
        )

    @admin.action(description="Restore selected users (reactivate)")
    def restore_users(self, request, queryset):
        restored = queryset.update(is_suspended=False, is_active=True)

        # Audit log
        try:
            from apps.admin_tools.models import AuditLog
            for uid in queryset.values_list("id", flat=True):
                AuditLog.objects.create(
                    admin_user=request.user,
                    action=AuditLog.Action.RESTORE,
                    target_type="accounts.User",
                    target_id=str(uid),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
        except Exception:
            pass

        messages.success(request, f"Restored {restored} users.")

    @admin.action(description="Force password reset (set unusable password)")
    def force_password_reset(self, request, queryset):
        count = 0
        for user in queryset:
            user.set_unusable_password()
            user.save(update_fields=["password"])
            count += 1
        messages.success(
            request,
            f"Password reset forced for {count} users. "
            f"They must use 'Forgot Password' to regain access.",
        )

    @admin.action(description="Grant 100 reward points")
    def grant_reward_points(self, request, queryset):
        try:
            from apps.rewards.models import RewardBalance, RewardPointsLedger

            count = 0
            for user in queryset:
                RewardPointsLedger.objects.create(
                    user=user,
                    points=100,
                    action_type="admin_grant",
                    description=f"Granted by {request.user.email} via admin",
                )
                balance, _ = RewardBalance.objects.get_or_create(user=user)
                balance.total_earned += 100
                balance.current_balance += 100
                balance.save(update_fields=["total_earned", "current_balance", "updated_at"])
                count += 1

            messages.success(request, f"Granted 100 points to {count} users.")
        except ImportError:
            messages.warning(request, "rewards app not available.")
        except Exception as e:
            messages.error(request, f"Failed to grant points: {e}")

    @admin.action(description="Broadcast notification to selected users")
    def broadcast_notification(self, request, queryset):
        count = 0
        for user in queryset.filter(is_active=True):
            Notification.objects.create(
                user=user,
                type=Notification.Type.POINTS_EARNED,
                title="Platform Update",
                body="Thank you for being part of Whydud!",
            )
            count += 1
        messages.success(request, f"Notification sent to {count} active users.")

    # ------------------------------------------------------------------
    # Stats header
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        total_users = User.objects.count()
        new_today = User.objects.filter(created_at__gte=today).count()
        new_this_week = User.objects.filter(created_at__gte=week_ago).count()
        active_7d = User.objects.filter(last_login_at__gte=week_ago).count()
        with_whydud_email = User.objects.filter(has_whydud_email=True).count()

        oauth_count = User.objects.filter(oauth_connections__isnull=False).distinct().count()
        oauth_pct = round(oauth_count / total_users * 100, 1) if total_users else 0
        password_pct = round(100 - oauth_pct, 1) if total_users else 0

        suspended_count = User.objects.filter(is_suspended=True).count()

        extra_context.update({
            "stats_header": True,
            "total_users": total_users,
            "new_today": new_today,
            "new_this_week": new_this_week,
            "active_7d": active_7d,
            "with_whydud_email": with_whydud_email,
            "oauth_pct": oauth_pct,
            "password_pct": password_pct,
            "suspended_count": suspended_count,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ------------------------------------------------------------------
# Other model admins
# ------------------------------------------------------------------

@admin.register(WhydudEmail)
class WhydudEmailAdmin(admin.ModelAdmin):
    list_display = ["username", "domain", "user", "is_active", "total_emails_received", "created_at"]
    list_filter = ["domain", "is_active"]
    search_fields = ["username", "user__email"]


@admin.register(OAuthConnection)
class OAuthConnectionAdmin(admin.ModelAdmin):
    list_display = ["user", "provider", "status", "connected_at", "last_sync_at"]
    list_filter = ["provider", "status"]
    search_fields = ["user__email"]
    readonly_fields = [
        "access_token_encrypted", "refresh_token_encrypted",
        "connected_at", "last_sync_at",
    ]


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ["user", "method_type", "bank_name", "card_variant", "is_preferred"]
    list_filter = ["method_type"]
    search_fields = ["user__email", "bank_name"]


@admin.register(ReservedUsername)
class ReservedUsernameAdmin(admin.ModelAdmin):
    list_display = ["username"]
    search_fields = ["username"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "type", "title", "is_read", "email_sent", "created_at"]
    list_filter = ["type", "is_read", "email_sent"]
    search_fields = ["user__email", "title"]
    readonly_fields = ["created_at"]
