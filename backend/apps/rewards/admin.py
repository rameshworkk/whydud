"""Enhanced rewards admin — Apex-style badges for points, status, balances."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import GiftCardCatalog, GiftCardRedemption, RewardBalance, RewardPointsLedger


@admin.register(RewardPointsLedger)
class RewardPointsLedgerAdmin(admin.ModelAdmin):
    list_display = ["user", "points_display", "action_badge", "reference_display", "created_ago", "expires_display"]
    list_filter = ["action_type"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at"]
    ordering = ["-created_at"]
    list_per_page = 30
    list_select_related = ["user"]

    @admin.display(description="Points", ordering="points")
    def points_display(self, obj):
        pts = obj.points or 0
        if pts > 0:
            return format_html(
                '<span class="text-[13px] font-semibold text-emerald-600 dark:text-emerald-400">+{}</span>',
                f"{pts:,}",
            )
        elif pts < 0:
            return format_html(
                '<span class="text-[13px] font-semibold text-red-600 dark:text-red-400">{}</span>',
                f"{pts:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Action")
    def action_badge(self, obj):
        action = obj.action_type or "\u2014"
        action_colors = {
            "review": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "referral": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "purchase": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "redemption": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "admin_grant": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
            "expiry": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "signup_bonus": "bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-400",
        }
        color = action_colors.get(
            action.lower() if action != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        label = action.replace("_", " ").title() if action != "\u2014" else action
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, label,
        )

    @admin.display(description="Reference")
    def reference_display(self, obj):
        ref = obj.reference_type or "\u2014"
        return format_html(
            '<span class="text-[12px] text-slate-500">{}</span>',
            ref.replace("_", " ").title() if ref != "\u2014" else ref,
        )

    @admin.display(description="Created", ordering="created_at")
    def created_ago(self, obj):
        if obj.created_at:
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
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Expires", ordering="expires_at")
    def expires_display(self, obj):
        if obj.expires_at:
            if obj.expires_at < timezone.now():
                return format_html(
                    '<span class="text-[12px] text-red-500 font-medium">Expired</span>'
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                obj.expires_at.strftime("%b %d, %Y"),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


@admin.register(RewardBalance)
class RewardBalanceAdmin(admin.ModelAdmin):
    list_display = ["user", "earned_display", "spent_display", "expired_display", "balance_display", "updated_ago"]
    search_fields = ["user__email"]
    readonly_fields = ["updated_at"]
    list_per_page = 30
    list_select_related = ["user"]

    @admin.display(description="Earned", ordering="total_earned")
    def earned_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-emerald-600 dark:text-emerald-400">{}</span>',
            f"{obj.total_earned:,}",
        )

    @admin.display(description="Spent", ordering="total_spent")
    def spent_display(self, obj):
        if obj.total_spent:
            return format_html(
                '<span class="text-[13px] font-medium text-slate-600 dark:text-slate-400">{}</span>',
                f"{obj.total_spent:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Expired", ordering="total_expired")
    def expired_display(self, obj):
        if obj.total_expired:
            return format_html(
                '<span class="text-[13px] font-medium text-red-500">{}</span>',
                f"{obj.total_expired:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Balance", ordering="current_balance")
    def balance_display(self, obj):
        bal = obj.current_balance or 0
        return format_html(
            '<span class="text-[13px] font-bold text-slate-800 dark:text-slate-200'
            ' inline-flex px-2.5 py-1 rounded-md bg-slate-100 dark:bg-slate-700">{}</span>',
            f"{bal:,}",
        )

    @admin.display(description="Updated")
    def updated_ago(self, obj):
        if obj.updated_at:
            delta = timezone.now() - obj.updated_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.updated_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.updated_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


@admin.register(GiftCardCatalog)
class GiftCardCatalogAdmin(admin.ModelAdmin):
    list_display = ["brand_display", "brand_slug", "active_badge", "category_badge"]
    list_filter = ["is_active", "category"]
    list_per_page = 30

    @admin.display(description="Brand", ordering="brand_name")
    def brand_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.brand_name,
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

    @admin.display(description="Category")
    def category_badge(self, obj):
        cat = obj.category or "\u2014"
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
            ' bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400">{}</span>',
            cat,
        )


@admin.register(GiftCardRedemption)
class GiftCardRedemptionAdmin(admin.ModelAdmin):
    list_display = ["user", "catalog", "denomination_display", "points_display", "status_badge", "created_ago"]
    list_filter = ["status"]
    search_fields = ["user__email"]
    readonly_fields = ["created_at", "fulfilled_at"]
    list_per_page = 30
    list_select_related = ["user", "catalog"]

    @admin.display(description="Denomination")
    def denomination_display(self, obj):
        if obj.denomination:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{int(obj.denomination):,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Points", ordering="points_spent")
    def points_display(self, obj):
        if obj.points_spent:
            return format_html(
                '<span class="text-[13px] font-medium text-amber-600 dark:text-amber-400">{}</span>',
                f"{obj.points_spent:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status = obj.status or "\u2014"
        status_colors = {
            "pending": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "fulfilled": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "cancelled": "bg-slate-100 text-slate-400 dark:bg-slate-500/20 dark:text-slate-500",
        }
        color = status_colors.get(
            status.lower() if status != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, status.title() if status != "\u2014" else status,
        )

    @admin.display(description="Created", ordering="created_at")
    def created_ago(self, obj):
        if obj.created_at:
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
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
