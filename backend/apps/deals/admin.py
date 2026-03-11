"""Enhanced deals admin — Apex-style badges for deal type, confidence, status."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import Deal


@admin.register(Deal)
class DealAdmin(admin.ModelAdmin):
    list_display = ["product_display", "type_badge", "price_display", "discount_badge", "confidence_badge", "active_badge", "detected_ago"]
    list_filter = ["deal_type", "confidence", "is_active"]
    search_fields = ["product__title"]
    list_select_related = ["product"]
    list_per_page = 30

    @admin.display(description="Product", ordering="product__title")
    def product_display(self, obj):
        t = obj.product.title if obj.product else "\u2014"
        short = t[:45] + "..." if len(t) > 45 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Type", ordering="deal_type")
    def type_badge(self, obj):
        dt = obj.deal_type or "\u2014"
        type_colors = {
            "price_drop": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "lightning": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "clearance": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "coupon": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "bank_offer": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = type_colors.get(dt, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        label = dt.replace("_", " ").title() if dt != "\u2014" else dt
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, label,
        )

    @admin.display(description="Price", ordering="current_price")
    def price_display(self, obj):
        if obj.current_price:
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{int(obj.current_price):,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Discount", ordering="discount_pct")
    def discount_badge(self, obj):
        if obj.discount_pct:
            pct = float(obj.discount_pct)
            if pct >= 50:
                classes = "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"
            elif pct >= 25:
                classes = "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
            else:
                classes = "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400"
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-semibold {}">{:.0f}%</span>',
                classes, pct,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Confidence", ordering="confidence")
    def confidence_badge(self, obj):
        conf = obj.confidence or "\u2014"
        conf_colors = {
            "high": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "medium": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "low": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        color = conf_colors.get(
            conf.lower() if conf != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, conf.title() if conf != "\u2014" else conf,
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
            '<span class="text-slate-400">Expired</span></span>'
        )

    @admin.display(description="Detected", ordering="detected_at")
    def detected_ago(self, obj):
        if obj.detected_at:
            delta = timezone.now() - obj.detected_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    obj.detected_at.strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.detected_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
