"""Enhanced user admin — Apex-style avatars, badges, tab filters, stats header."""
from datetime import timedelta

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from apps.admin_tools.mixins import AuditLogMixin

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
class UserAdmin(AuditLogMixin, BaseUserAdmin):
    change_list_template = "admin/accounts/user/change_list.html"

    list_display = [
        "user_display",
        "role_badge",
        "active_badge",
        "subscription_display",
        "review_count_display",
        "whydud_email_display",
        "last_active_display",
    ]
    list_filter = []  # Empty — we use custom tab filters instead
    search_fields = ["email", "name"]
    ordering = ["-created_at"]
    list_per_page = 25
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
        qs = super().get_queryset(request).annotate(
            _review_count=Count("reviews"),
        )
        # Apply tab filter
        status = request.GET.get("status")
        if status == "active":
            qs = qs.filter(is_active=True)
        elif status == "inactive":
            qs = qs.filter(is_active=False)
        elif status == "suspended":
            qs = qs.filter(is_suspended=True)
        return qs

    # ------------------------------------------------------------------
    # Display columns — Apex-style with avatars and badges
    # ------------------------------------------------------------------

    @admin.display(description="User", ordering="email")
    def user_display(self, obj):
        name = obj.name or obj.email.split("@")[0]
        parts = name.split()
        initials = (parts[0][0] + (parts[1][0] if len(parts) > 1 else "")).upper()

        colors = [
            "bg-emerald-500", "bg-blue-500", "bg-violet-500", "bg-amber-500",
            "bg-rose-500", "bg-cyan-500", "bg-indigo-500", "bg-pink-500",
        ]
        color = colors[ord(initials[0]) % len(colors)]

        return format_html(
            '<div class="flex items-center gap-3">'
            '  <div class="w-9 h-9 rounded-full {} text-white flex items-center'
            '       justify-center text-xs font-semibold flex-shrink-0">{}</div>'
            '  <div>'
            '    <div class="text-[13px] font-medium text-slate-900 dark:text-slate-100">{}</div>'
            '    <div class="text-[12px] text-slate-400">{}</div>'
            '  </div>'
            '</div>',
            color, initials, name, obj.email,
        )

    @admin.display(description="Role")
    def role_badge(self, obj):
        role = obj.get_role_display() if obj.role else "Registered"
        role_colors = {
            "Admin": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "Super Admin": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "Moderator": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "Senior Moderator": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "Premium": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "Data Ops": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "Fraud Analyst": "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-400",
            "Trust Engineer": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
            "Connected": "bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-400",
        }
        color_class = role_colors.get(role, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-medium {}">{}</span>',
            color_class, role,
        )

    @admin.display(description="Status", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_suspended:
            return format_html(
                '<span class="inline-flex items-center gap-1.5 text-[12px]">'
                '  <span class="w-2 h-2 rounded-full bg-amber-500"></span>'
                '  <span class="text-amber-600 dark:text-amber-400 font-medium">Suspended</span>'
                '</span>'
            )
        if obj.is_active:
            return format_html(
                '<span class="inline-flex items-center gap-1.5 text-[12px]">'
                '  <span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '  <span class="text-emerald-600 dark:text-emerald-400 font-medium">Active</span>'
                '</span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1.5 text-[12px]">'
            '  <span class="w-2 h-2 rounded-full bg-red-500"></span>'
            '  <span class="text-red-600 dark:text-red-400 font-medium">Inactive</span>'
            '</span>'
        )

    @admin.display(description="Plan")
    def subscription_display(self, obj):
        if obj.subscription_tier == User.SubscriptionTier.PREMIUM:
            return format_html(
                '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-medium'
                ' bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">'
                'Premium</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">Free</span>')

    @admin.display(description="Reviews", ordering="_review_count")
    def review_count_display(self, obj):
        count = obj._review_count
        if count > 0:
            return format_html(
                '<span class="text-[13px] font-medium text-slate-700 dark:text-slate-300">{}</span>',
                count,
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="@whyd.*")
    def whydud_email_display(self, obj):
        if obj.has_whydud_email:
            try:
                we = obj.whydud_email
                if we:
                    return format_html(
                        '<span class="text-[12px] text-emerald-500 font-medium">{}@{}</span>',
                        we.username, we.domain,
                    )
            except WhydudEmail.DoesNotExist:
                pass
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Last Active", ordering="last_login_at")
    def last_active_display(self, obj):
        if obj.last_login_at:
            delta = timezone.now() - obj.last_login_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.last_login_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.last_login_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">Never</span>')

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
        active_count = User.objects.filter(is_active=True).count()
        inactive_count = User.objects.filter(is_active=False).count()

        # Tab filter state
        current_tab = request.GET.get("status", "all")

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
            "active_count": active_count,
            "inactive_count": inactive_count,
            "current_tab": current_tab,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ------------------------------------------------------------------
# Other model admins
# ------------------------------------------------------------------

@admin.register(WhydudEmail)
class WhydudEmailAdmin(admin.ModelAdmin):
    list_display = [
        "email_display", "user", "active_badge",
        "emails_badge", "orders_badge", "last_email_display",
    ]
    list_filter = ["domain", "is_active"]
    search_fields = ["username", "user__email"]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Email")
    def email_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-emerald-600 dark:text-emerald-400">'
            '{}@{}</span>',
            obj.username, obj.domain,
        )

    @admin.display(description="Active", ordering="is_active")
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Active</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>'
            '<span class="text-slate-400">Inactive</span></span>'
        )

    @admin.display(description="Emails", ordering="total_emails_received")
    def emails_badge(self, obj):
        count = obj.total_emails_received or 0
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                f"{count:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Orders", ordering="total_orders_detected")
    def orders_badge(self, obj):
        count = obj.total_orders_detected or 0
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400">{}</span>',
                f"{count:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Last Email", ordering="last_email_received_at")
    def last_email_display(self, obj):
        if obj.last_email_received_at:
            delta = timezone.now() - obj.last_email_received_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.last_email_received_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.last_email_received_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">Never</span>')


@admin.register(OAuthConnection)
class OAuthConnectionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "provider_badge", "status_badge",
        "connected_ago", "synced_ago",
    ]
    list_filter = ["provider", "status"]
    search_fields = ["user__email"]
    readonly_fields = [
        "access_token_encrypted", "refresh_token_encrypted",
        "connected_at", "last_sync_at",
    ]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Provider", ordering="provider")
    def provider_badge(self, obj):
        provider = obj.provider or "\u2014"
        provider_colors = {
            "google": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "gmail": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "microsoft": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "outlook": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = provider_colors.get(
            provider.lower() if provider != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, provider.title() if provider != "\u2014" else provider,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status = obj.status or "\u2014"
        status_colors = {
            "active": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "connected": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "expired": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "revoked": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "error": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        color = status_colors.get(
            status.lower() if status != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, status.title() if status != "\u2014" else status,
        )

    @admin.display(description="Connected", ordering="connected_at")
    def connected_ago(self, obj):
        if obj.connected_at:
            delta = timezone.now() - obj.connected_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.connected_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.connected_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Last Sync", ordering="last_sync_at")
    def synced_ago(self, obj):
        if obj.last_sync_at:
            delta = timezone.now() - obj.last_sync_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.last_sync_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.last_sync_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">Never</span>')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = [
        "user", "type_badge", "bank_display",
        "card_variant", "preferred_badge",
    ]
    list_filter = ["method_type"]
    search_fields = ["user__email", "bank_name"]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Type", ordering="method_type")
    def type_badge(self, obj):
        mt = obj.method_type or "\u2014"
        type_colors = {
            "credit": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "debit": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "upi": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "wallet": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "netbanking": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = type_colors.get(
            mt.lower() if mt != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, mt.title() if mt != "\u2014" else mt,
        )

    @admin.display(description="Bank")
    def bank_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.bank_name or "\u2014",
        )

    @admin.display(description="Preferred", ordering="is_preferred")
    def preferred_badge(self, obj):
        if obj.is_preferred:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">Preferred</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


@admin.register(ReservedUsername)
class ReservedUsernameAdmin(admin.ModelAdmin):
    list_display = ["username"]
    search_fields = ["username"]


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ["user", "type_badge", "title_short", "is_read_badge", "email_sent_badge", "created_ago"]
    list_filter = ["type", "is_read", "email_sent"]
    search_fields = ["user__email", "title"]
    readonly_fields = ["created_at"]
    list_per_page = 30
    list_select_related = ["user"]

    @admin.display(description="Type")
    def type_badge(self, obj):
        type_colors = {
            "price_drop": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "price_alert": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "back_in_stock": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "order_detected": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "points_earned": "bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-400",
            "level_up": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = type_colors.get(obj.type, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, obj.get_type_display(),
        )

    @admin.display(description="Title")
    def title_short(self, obj):
        t = obj.title
        short = t[:50] + "..." if len(t) > 50 else t
        return format_html('<span class="text-[13px] text-slate-700 dark:text-slate-300">{}</span>', short)

    @admin.display(description="Read", ordering="is_read")
    def is_read_badge(self, obj):
        if obj.is_read:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400">Read</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-blue-500"></span>'
            '<span class="text-blue-600 dark:text-blue-400">Unread</span></span>'
        )

    @admin.display(description="Emailed", ordering="email_sent")
    def email_sent_badge(self, obj):
        if obj.email_sent:
            return format_html(
                '<span class="text-[12px] text-emerald-500 font-medium">Sent</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Created")
    def created_ago(self, obj):
        delta = timezone.now() - obj.created_at
        if delta.days > 30:
            return format_html(
                '<span class="text-[12px] text-slate-400">{}</span>',
                obj.created_at.strftime("%b %d, %Y"),
            )
        return format_html(
            '<span class="text-[12px] text-slate-500">{} ago</span>',
            timesince(obj.created_at, timezone.now()).split(",")[0],
        )
