"""Enhanced email intel admin — Apex-style badges for parse status, categories."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import DetectedSubscription, InboxEmail, ParsedOrder, RefundTracking, ReturnWindow


@admin.register(InboxEmail)
class InboxEmailAdmin(admin.ModelAdmin):
    list_display = ["user", "sender_display", "subject_display", "category_badge", "parse_status_badge", "received_ago"]
    list_filter = ["category", "parse_status"]
    search_fields = ["sender_address", "subject"]
    list_per_page = 30
    list_select_related = ["user"]
    # NOTE: body fields contain encrypted data — never display in admin

    @admin.display(description="Sender")
    def sender_display(self, obj):
        return format_html(
            '<span class="text-[12px] font-mono text-slate-600 dark:text-slate-400">{}</span>',
            obj.sender_address[:40] if obj.sender_address else "\u2014",
        )

    @admin.display(description="Subject")
    def subject_display(self, obj):
        s = obj.subject or "\u2014"
        short = s[:50] + "..." if len(s) > 50 else s
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Category")
    def category_badge(self, obj):
        cat = obj.category or "\u2014"
        cat_colors = {
            "order": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "shipping": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "return": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "refund": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "subscription": "bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-400",
            "promo": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = cat_colors.get(
            cat.lower() if cat != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, cat.title() if cat != "\u2014" else cat,
        )

    @admin.display(description="Status")
    def parse_status_badge(self, obj):
        status = obj.parse_status or "\u2014"
        status_colors = {
            "parsed": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "pending": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "skipped": "bg-slate-100 text-slate-400 dark:bg-slate-500/20 dark:text-slate-500",
        }
        color = status_colors.get(
            status.lower() if status != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, status.title() if status != "\u2014" else status,
        )

    @admin.display(description="Received", ordering="received_at")
    def received_ago(self, obj):
        if obj.received_at:
            delta = timezone.now() - obj.received_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.received_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.received_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


@admin.register(ParsedOrder)
class ParsedOrderAdmin(admin.ModelAdmin):
    list_display = ["user", "marketplace_badge", "product_display", "amount_display", "order_date_display"]
    list_filter = ["marketplace", "source"]
    search_fields = ["product_name", "order_id"]
    list_per_page = 30
    list_select_related = ["user"]

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        mp = obj.marketplace or "\u2014"
        colors = {
            "amazon": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "myntra": "bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-400",
        }
        color = colors.get(
            mp.lower() if mp != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, mp.title() if mp != "\u2014" else mp,
        )

    @admin.display(description="Product")
    def product_display(self, obj):
        name = obj.product_name or "\u2014"
        short = name[:50] + "..." if len(name) > 50 else name
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Amount", ordering="total_amount")
    def amount_display(self, obj):
        if obj.total_amount:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{int(obj.total_amount):,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Order Date", ordering="order_date")
    def order_date_display(self, obj):
        if obj.order_date:
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                obj.order_date.strftime("%b %d, %Y"),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


# ------------------------------------------------------------------
# RefundTrackingAdmin
# ------------------------------------------------------------------

@admin.register(RefundTracking)
class RefundTrackingAdmin(admin.ModelAdmin):
    list_display = [
        "user", "marketplace_badge", "status_badge",
        "amount_display", "delay_badge", "initiated_ago",
    ]
    list_filter = ["status", "marketplace"]
    search_fields = ["user__email"]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        mp = obj.marketplace or "\u2014"
        colors = {
            "amazon": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = colors.get(
            mp.lower() if mp != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, mp.title() if mp != "\u2014" else mp,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status = obj.status or "\u2014"
        status_colors = {
            "initiated": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "processing": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "completed": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "delayed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        color = status_colors.get(
            status.lower() if status != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, status.title() if status != "\u2014" else status,
        )

    @admin.display(description="Amount", ordering="refund_amount")
    def amount_display(self, obj):
        if obj.refund_amount:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{int(obj.refund_amount):,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Delay", ordering="delay_days")
    def delay_badge(self, obj):
        if obj.delay_days is not None and obj.delay_days > 0:
            if obj.delay_days >= 7:
                classes = "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"
            elif obj.delay_days >= 3:
                classes = "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
            else:
                classes = "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400"
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">'
                '{}d late</span>',
                classes, obj.delay_days,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Initiated", ordering="initiated_at")
    def initiated_ago(self, obj):
        if obj.initiated_at:
            delta = timezone.now() - obj.initiated_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.initiated_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.initiated_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


# ------------------------------------------------------------------
# ReturnWindowAdmin
# ------------------------------------------------------------------

@admin.register(ReturnWindow)
class ReturnWindowAdmin(admin.ModelAdmin):
    list_display = [
        "user", "order", "window_status_badge",
        "extended_badge", "alerts_display",
    ]
    search_fields = ["user__email"]
    list_select_related = ["user", "order"]
    list_per_page = 30

    @admin.display(description="Window Status")
    def window_status_badge(self, obj):
        from datetime import date
        today = date.today()
        days_left = (obj.window_end_date - today).days if obj.window_end_date else None

        if days_left is None:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        if days_left < 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">Expired</span>'
            )
        if days_left <= 3:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">'
                '{}d left</span>',
                days_left,
            )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
            ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">'
            '{}d left</span>',
            days_left,
        )

    @admin.display(description="Extended", ordering="is_extended")
    def extended_badge(self, obj):
        if obj.is_extended:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">Extended</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Alerts")
    def alerts_display(self, obj):
        parts = []
        if obj.alert_sent_3day:
            parts.append("3d")
        if obj.alert_sent_1day:
            parts.append("1d")
        if parts:
            return format_html(
                '<span class="text-[12px] text-emerald-500 font-medium">Sent: {}</span>',
                ", ".join(parts),
            )
        return format_html('<span class="text-[12px] text-slate-400">None</span>')


# ------------------------------------------------------------------
# DetectedSubscriptionAdmin
# ------------------------------------------------------------------

@admin.register(DetectedSubscription)
class DetectedSubscriptionAdmin(admin.ModelAdmin):
    list_display = [
        "user", "service_display", "amount_display",
        "cycle_badge", "active_badge", "renewal_display",
    ]
    list_filter = ["is_active", "billing_cycle"]
    search_fields = ["user__email", "service_name"]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Service", ordering="service_name")
    def service_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.service_name,
        )

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        if obj.amount:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{int(obj.amount):,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Cycle", ordering="billing_cycle")
    def cycle_badge(self, obj):
        cycle = obj.billing_cycle or "\u2014"
        cycle_colors = {
            "monthly": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "yearly": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "quarterly": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
            "weekly": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
        }
        color = cycle_colors.get(
            cycle.lower() if cycle != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, cycle.title() if cycle != "\u2014" else cycle,
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
            '<span class="text-slate-400">Cancelled</span></span>'
        )

    @admin.display(description="Next Renewal", ordering="next_renewal")
    def renewal_display(self, obj):
        if obj.next_renewal:
            from datetime import date
            days_until = (obj.next_renewal - date.today()).days
            if days_until < 0:
                return format_html(
                    '<span class="text-[12px] text-red-500 font-medium">Overdue</span>'
                )
            if days_until <= 7:
                return format_html(
                    '<span class="text-[12px] text-amber-500 font-medium">In {}d</span>',
                    days_until,
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                obj.next_renewal.strftime("%b %d, %Y"),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
