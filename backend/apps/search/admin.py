"""Enhanced search admin — Apex-style badges for latency and results."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import SearchLog


@admin.register(SearchLog)
class SearchLogAdmin(admin.ModelAdmin):
    list_display = ["query_display", "results_badge", "latency_badge", "searched_ago"]
    readonly_fields = ["query", "results_count", "latency_ms", "filters_used", "created_at"]
    list_per_page = 30

    @admin.display(description="Query")
    def query_display(self, obj):
        q = obj.query or "\u2014"
        short = q[:60] + "..." if len(q) > 60 else q
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Results", ordering="results_count")
    def results_badge(self, obj):
        count = obj.results_count or 0
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                f"{count:,}",
            )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px]'
            ' bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">0</span>'
        )

    @admin.display(description="Latency", ordering="latency_ms")
    def latency_badge(self, obj):
        ms = obj.latency_ms
        if ms is not None:
            if ms < 100:
                classes = "text-emerald-600 dark:text-emerald-400"
            elif ms < 500:
                classes = "text-amber-600 dark:text-amber-400"
            else:
                classes = "text-red-600 dark:text-red-400"
            return format_html(
                '<span class="text-[12px] font-mono font-medium {}">{:.0f}ms</span>',
                classes, ms,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Searched", ordering="created_at")
    def searched_ago(self, obj):
        if obj.created_at:
            delta = timezone.now() - obj.created_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.created_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.created_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
