"""Enhanced wishlists admin — Apex-style badges."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Wishlist, WishlistItem


@admin.register(Wishlist)
class WishlistAdmin(admin.ModelAdmin):
    list_display = ["user", "name_display", "default_badge", "visibility_badge", "item_count"]
    search_fields = ["user__email", "name"]
    list_select_related = ["user"]
    list_per_page = 30

    @admin.display(description="Name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name or "Untitled",
        )

    @admin.display(description="Default", ordering="is_default")
    def default_badge(self, obj):
        if obj.is_default:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">Default</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Visibility", ordering="is_public")
    def visibility_badge(self, obj):
        if obj.is_public:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-blue-500"></span>'
                '<span class="text-blue-600 dark:text-blue-400 font-medium">Public</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>'
            '<span class="text-slate-400">Private</span></span>'
        )

    @admin.display(description="Items")
    def item_count(self, obj):
        count = obj.items.count()
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                count,
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')


@admin.register(WishlistItem)
class WishlistItemAdmin(admin.ModelAdmin):
    list_display = ["wishlist", "product", "added_display"]
    list_select_related = ["wishlist", "product"]
    list_per_page = 30

    @admin.display(description="Added")
    def added_display(self, obj):
        if hasattr(obj, "created_at") and obj.created_at:
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                obj.created_at.strftime("%b %d, %Y"),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
