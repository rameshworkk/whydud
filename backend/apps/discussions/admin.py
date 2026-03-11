"""Enhanced discussions admin — Apex-style badges for thread types, status."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from .models import DiscussionThread, DiscussionReply


@admin.register(DiscussionThread)
class DiscussionThreadAdmin(admin.ModelAdmin):
    list_display = ["title_display", "product_display", "type_badge", "replies_badge", "pinned_badge", "removed_badge", "created_ago"]
    list_filter = ["thread_type", "is_removed", "is_pinned"]
    search_fields = ["title", "body"]
    list_select_related = ["product"]
    list_per_page = 30

    @admin.display(description="Title", ordering="title")
    def title_display(self, obj):
        t = obj.title or "\u2014"
        short = t[:50] + "..." if len(t) > 50 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Product")
    def product_display(self, obj):
        if obj.product:
            t = obj.product.title
            short = t[:35] + "..." if len(t) > 35 else t
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>', short,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Type", ordering="thread_type")
    def type_badge(self, obj):
        tt = obj.thread_type or "\u2014"
        type_colors = {
            "question": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "discussion": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "review": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "tip": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
        }
        color = type_colors.get(
            tt.lower() if tt != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, tt.title() if tt != "\u2014" else tt,
        )

    @admin.display(description="Replies", ordering="reply_count")
    def replies_badge(self, obj):
        count = obj.reply_count or 0
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                count,
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Pinned", ordering="is_pinned")
    def pinned_badge(self, obj):
        if obj.is_pinned:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">Pinned</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Status", ordering="is_removed")
    def removed_badge(self, obj):
        if obj.is_removed:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">Removed</span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
            '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Visible</span></span>'
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


@admin.register(DiscussionReply)
class DiscussionReplyAdmin(admin.ModelAdmin):
    list_display = ["thread", "user", "accepted_badge", "removed_badge", "created_ago"]
    list_per_page = 30

    @admin.display(description="Accepted", ordering="is_accepted")
    def accepted_badge(self, obj):
        if obj.is_accepted:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">Accepted</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Status", ordering="is_removed")
    def removed_badge(self, obj):
        if obj.is_removed:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">Removed</span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
            '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Visible</span></span>'
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
