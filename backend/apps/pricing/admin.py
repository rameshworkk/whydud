"""Enhanced pricing admin — Apex-style badges, click tracking, price alerts, backfill management."""
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from apps.admin_tools.mixins import AuditLogMixin

from .models import (
    BackfillProduct,
    ClickEvent,
    EnrichmentPriorityRule,
    MarketplaceOffer,
    PriceAlert,
)


# ------------------------------------------------------------------
# ClickEventAdmin
# ------------------------------------------------------------------

@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/pricing/clickevent/change_list.html"

    list_display = [
        "product_title",
        "marketplace_badge",
        "source_page_badge",
        "price_display",
        "affiliate_tag",
        "purchase_badge",
        "device_badge",
        "clicked_ago",
    ]
    list_filter = [
        "marketplace",
        "source_page",
        "purchase_confirmed",
        "device_type",
        "clicked_at",
    ]
    search_fields = ["product__title", "affiliate_tag", "user__email"]
    readonly_fields = [
        "id", "ip_hash", "user_agent_hash", "clicked_at",
        "affiliate_url",
    ]
    list_per_page = 30
    list_select_related = ["product", "marketplace"]
    raw_id_fields = ["product", "listing", "user", "marketplace"]
    date_hierarchy = "clicked_at"

    # ------------------------------------------------------------------
    # Display columns — Apex-style
    # ------------------------------------------------------------------

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        short = t[:50] + "..." if len(t) > 50 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        name = obj.marketplace.name if obj.marketplace else "\u2014"
        colors = {
            "Amazon.in": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "Flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = colors.get(name, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, name,
        )

    @admin.display(description="Source")
    def source_page_badge(self, obj):
        page = obj.source_page or "\u2014"
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
            ' bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400">{}</span>',
            page,
        )

    @admin.display(description="Price", ordering="price_at_click")
    def price_display(self, obj):
        if obj.price_at_click is not None:
            p = int(obj.price_at_click) // 100
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{p:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Purchased", ordering="purchase_confirmed")
    def purchase_badge(self, obj):
        if obj.purchase_confirmed:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Yes</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>'
            '<span class="text-slate-400">No</span></span>'
        )

    @admin.display(description="Device")
    def device_badge(self, obj):
        device = obj.device_type or "\u2014"
        device_colors = {
            "mobile": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "desktop": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "tablet": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = device_colors.get(
            device.lower() if device else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, device.title() if device != "\u2014" else device,
        )

    @admin.display(description="Clicked", ordering="clicked_at")
    def clicked_ago(self, obj):
        if obj.clicked_at:
            delta = timezone.now() - obj.clicked_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.clicked_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.clicked_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    # ------------------------------------------------------------------
    # Stats header
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)

        clicks_today = ClickEvent.objects.filter(clicked_at__gte=today).count()
        clicks_week = ClickEvent.objects.filter(clicked_at__gte=week_ago).count()
        clicks_month = ClickEvent.objects.filter(clicked_at__gte=month_ago).count()

        # By marketplace (top 5)
        by_marketplace = list(
            ClickEvent.objects.filter(clicked_at__gte=week_ago)
            .values("marketplace__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Top 5 products this week
        top_products = list(
            ClickEvent.objects.filter(clicked_at__gte=week_ago)
            .values("product__title")
            .annotate(count=Count("id"))
            .order_by("-count")[:5]
        )

        # Conversion rate
        confirmed_week = ClickEvent.objects.filter(
            clicked_at__gte=week_ago, purchase_confirmed=True,
        ).count()
        conversion_rate = round(confirmed_week / clicks_week * 100, 1) if clicks_week else 0

        extra_context.update({
            "stats_header": True,
            "clicks_today": clicks_today,
            "clicks_week": clicks_week,
            "clicks_month": clicks_month,
            "by_marketplace": by_marketplace,
            "top_products": top_products,
            "conversion_rate": conversion_rate,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ------------------------------------------------------------------
# PriceAlertAdmin
# ------------------------------------------------------------------

@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    list_display = [
        "user_display",
        "product_title",
        "target_price_display",
        "current_price_display",
        "price_comparison",
        "marketplace_badge",
        "active_badge",
        "triggered_badge",
        "triggered_ago",
    ]
    list_filter = ["is_active", "is_triggered", "marketplace"]
    search_fields = ["user__email", "product__title"]
    readonly_fields = [
        "id", "created_at", "updated_at",
        "triggered_at", "triggered_price", "triggered_marketplace",
    ]
    list_select_related = ["user", "product", "marketplace"]
    raw_id_fields = ["user", "product"]
    list_per_page = 30

    @admin.display(description="User", ordering="user__email")
    def user_display(self, obj):
        return format_html(
            '<span class="text-[13px] text-slate-700 dark:text-slate-300">{}</span>',
            obj.user.email,
        )

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        short = t[:40] + "..." if len(t) > 40 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Target", ordering="target_price")
    def target_price_display(self, obj):
        p = int(obj.target_price) // 100
        return format_html(
            '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
            f"\u20b9{p:,}",
        )

    @admin.display(description="Current", ordering="current_price")
    def current_price_display(self, obj):
        if obj.current_price is not None:
            p = int(obj.current_price) // 100
            return format_html(
                '<span class="text-[13px] text-slate-600 dark:text-slate-400">{}</span>',
                f"\u20b9{p:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="vs Target")
    def price_comparison(self, obj):
        if obj.current_price and obj.target_price:
            if obj.current_price <= obj.target_price:
                return format_html(
                    '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                    ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">Below</span>'
                )
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400">Above</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        if obj.marketplace:
            name = obj.marketplace.name
            colors = {
                "Amazon.in": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
                "Flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            }
            color = colors.get(name, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
                color, name,
            )
        return format_html('<span class="text-[12px] text-slate-400">Any</span>')

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

    @admin.display(description="Triggered", ordering="is_triggered")
    def triggered_badge(self, obj):
        if obj.is_triggered:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">Triggered</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Triggered At", ordering="triggered_at")
    def triggered_ago(self, obj):
        if obj.triggered_at:
            delta = timezone.now() - obj.triggered_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.triggered_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.triggered_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


# ------------------------------------------------------------------
# MarketplaceOfferAdmin
# ------------------------------------------------------------------

@admin.register(MarketplaceOffer)
class MarketplaceOfferAdmin(admin.ModelAdmin):
    list_display = ["title_display", "marketplace_badge", "offer_type_badge", "bank_slug", "active_badge", "valid_until_display"]
    list_filter = ["is_active", "offer_type", "marketplace"]
    search_fields = ["title", "bank_slug"]
    list_per_page = 30

    @admin.display(description="Title")
    def title_display(self, obj):
        t = obj.title
        short = t[:50] + "..." if len(t) > 50 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        name = str(obj.marketplace) if obj.marketplace else "\u2014"
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
            ' bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400">{}</span>',
            name,
        )

    @admin.display(description="Type")
    def offer_type_badge(self, obj):
        type_colors = {
            "cashback": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "discount": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "emi": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "coupon": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
        }
        offer_type = obj.offer_type or "\u2014"
        color = type_colors.get(
            offer_type.lower() if offer_type else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, offer_type.title() if offer_type != "\u2014" else offer_type,
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

    @admin.display(description="Valid Until")
    def valid_until_display(self, obj):
        if obj.valid_until:
            if obj.valid_until < timezone.now():
                return format_html(
                    '<span class="text-[12px] text-red-500 font-medium">Expired {}</span>',
                    timezone.localtime(obj.valid_until).strftime("%b %d"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                timezone.localtime(obj.valid_until).strftime("%b %d, %Y"),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')


# ------------------------------------------------------------------
# BackfillProductAdmin
# ------------------------------------------------------------------

@admin.register(BackfillProduct)
class BackfillProductAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = [
        "external_id_display",
        "marketplace_badge",
        "title_display",
        "status_badge",
        "scrape_status_badge",
        "priority_badge",
        "method_badge",
        "review_status_badge",
        "data_points_display",
        "created_ago",
    ]
    list_filter = [
        "status", "scrape_status", "enrichment_priority",
        "enrichment_method", "review_status", "marketplace_slug",
    ]
    search_fields = ["external_id", "title", "ph_code"]
    readonly_fields = ["id", "created_at", "updated_at", "raw_price_data"]
    list_per_page = 30
    actions = [
        "mark_for_reviews",
        "set_priority_p0",
        "set_priority_p1",
        "set_priority_p2",
        "set_priority_p3",
        "apply_custom_rules",
    ]

    @admin.display(description="External ID")
    def external_id_display(self, obj):
        return format_html(
            '<span class="text-[12px] font-mono text-slate-600 dark:text-slate-400">{}</span>',
            obj.external_id[:20] if obj.external_id else "\u2014",
        )

    @admin.display(description="Marketplace")
    def marketplace_badge(self, obj):
        slug = obj.marketplace_slug or "\u2014"
        colors = {
            "amazon-in": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
        }
        color = colors.get(slug, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, slug,
        )

    @admin.display(description="Title")
    def title_display(self, obj):
        t = obj.title or "\u2014"
        short = t[:45] + "..." if len(t) > 45 else t
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            short,
        )

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj):
        status_colors = {
            "Discovered": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "PH Extended": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "Done": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "Failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        status = obj.status or "\u2014"
        classes = status_colors.get(status, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, status,
        )

    @admin.display(description="Scrape", ordering="scrape_status")
    def scrape_status_badge(self, obj):
        scrape_colors = {
            "pending": "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
            "enriching": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "scraped": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        status = obj.scrape_status or "\u2014"
        classes = scrape_colors.get(status, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, status,
        )

    @admin.display(description="Priority", ordering="enrichment_priority")
    def priority_badge(self, obj):
        p = obj.enrichment_priority
        if p is None:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        priority_colors = {
            0: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            1: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            2: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            3: "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        }
        classes = priority_colors.get(p, priority_colors[3])
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-semibold {}">P{}</span>',
            classes, p,
        )

    @admin.display(description="Method", ordering="enrichment_method")
    def method_badge(self, obj):
        method = obj.enrichment_method or "pending"
        method_colors = {
            "pending": "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
            "playwright": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "curl_cffi": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
            "skipped": "bg-slate-100 text-slate-400 dark:bg-slate-500/20 dark:text-slate-500",
        }
        classes = method_colors.get(method, method_colors["pending"])
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, method,
        )

    @admin.display(description="Reviews", ordering="review_status")
    def review_status_badge(self, obj):
        review_colors = {
            "skip": "bg-slate-100 text-slate-400 dark:bg-slate-500/20 dark:text-slate-500",
            "pending": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "scraping": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "scraped": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "failed": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        status = obj.review_status or "skip"
        classes = review_colors.get(status, review_colors["skip"])
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, status,
        )

    @admin.display(description="Data Pts")
    def data_points_display(self, obj):
        count = obj.price_data_points or 0
        cached = len(obj.raw_price_data) if obj.raw_price_data else 0
        if count > 0 or cached > 0:
            return format_html(
                '<span class="text-[13px] font-medium text-slate-700 dark:text-slate-300">{}</span>'
                '<span class="text-[11px] text-slate-400 ml-1">({}c)</span>',
                count, cached,
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

    @admin.display(description="Created")
    def created_ago(self, obj):
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

    @admin.action(description="Mark for review scraping")
    def mark_for_reviews(self, request, queryset):
        updated = queryset.filter(scrape_status="scraped").update(review_status="pending")
        self.message_user(request, f"{updated} products marked for review scraping.")

    @admin.action(description="Set priority → P0 (on-demand)")
    def set_priority_p0(self, request, queryset):
        updated = queryset.filter(scrape_status="pending").update(enrichment_priority=0)
        self.message_user(request, f"{updated} products set to P0 (on-demand).")

    @admin.action(description="Set priority → P1 (Playwright)")
    def set_priority_p1(self, request, queryset):
        updated = queryset.filter(scrape_status="pending").update(enrichment_priority=1)
        self.message_user(request, f"{updated} products set to P1 (Playwright).")

    @admin.action(description="Set priority → P2 (curl_cffi)")
    def set_priority_p2(self, request, queryset):
        updated = queryset.filter(scrape_status="pending").update(enrichment_priority=2)
        self.message_user(request, f"{updated} products set to P2 (curl_cffi).")

    @admin.action(description="Set priority → P3 (curl_cffi-low)")
    def set_priority_p3(self, request, queryset):
        updated = queryset.filter(scrape_status="pending").update(enrichment_priority=3)
        self.message_user(request, f"{updated} products set to P3 (curl_cffi-low).")

    @admin.action(description="Apply custom priority rules")
    def apply_custom_rules(self, request, queryset):
        from apps.pricing.backfill.prioritizer import apply_custom_priority_rules
        result = apply_custom_priority_rules()
        total = result["total"]
        rule_count = len(result["rules"])
        self.message_user(
            request,
            f"Applied {rule_count} rules — {total} products updated.",
        )


# ------------------------------------------------------------------
# EnrichmentPriorityRuleAdmin
# ------------------------------------------------------------------

@admin.register(EnrichmentPriorityRule)
class EnrichmentPriorityRuleAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = [
        "name_display",
        "active_badge",
        "order_display",
        "filters_summary",
        "target_badge",
        "reviews_badge",
        "preview_count_display",
        "updated_ago",
    ]
    list_filter = ["is_active", "target_priority", "marketplace_slug"]
    search_fields = ["name", "category_name", "brand_pattern", "title_contains"]
    list_editable = ["is_active", "order"]
    list_per_page = 30
    readonly_fields = ["id", "created_at", "updated_at", "preview_count_display"]
    actions = ["apply_selected_rules", "deactivate_rules", "activate_rules"]

    # Use non-display versions for list_editable
    list_display = [
        "name_display",
        "is_active",
        "order",
        "filters_summary",
        "target_badge",
        "reviews_badge",
        "preview_count_display",
        "updated_ago",
    ]

    fieldsets = [
        (None, {
            "fields": ("name", "is_active", "order"),
        }),
        ("Filters (all optional — combined with AND)", {
            "fields": (
                "marketplace_slug",
                ("category_name", "category_pattern"),
                ("brand_pattern", "title_contains"),
                ("min_price", "max_price"),
                "min_data_points",
            ),
            "description": (
                "Leave filters blank to match all products. "
                "Prices are in paisa (₹100 = 10000 paisa). "
                "Patterns use PostgreSQL regex syntax."
            ),
        }),
        ("Target", {
            "fields": ("target_priority", "also_mark_reviews"),
        }),
    ]

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------

    @admin.display(description="Rule Name", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name,
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
            '<span class="text-slate-400">Off</span></span>'
        )

    @admin.display(description="Order", ordering="order")
    def order_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-mono text-slate-500">{}</span>',
            obj.order,
        )

    @admin.display(description="Filters")
    def filters_summary(self, obj):
        parts = []
        if obj.marketplace_slug:
            parts.append(f"marketplace={obj.marketplace_slug}")
        if obj.category_name:
            parts.append(f"cat={obj.category_name}")
        if obj.category_pattern:
            parts.append(f"cat~{obj.category_pattern[:30]}")
        if obj.brand_pattern:
            parts.append(f"brand~{obj.brand_pattern[:30]}")
        if obj.title_contains:
            parts.append(f'title*"{obj.title_contains[:20]}"')
        if obj.min_price is not None:
            parts.append(f"price≥₹{int(obj.min_price) // 100:,}")
        if obj.max_price is not None:
            parts.append(f"price≤₹{int(obj.max_price) // 100:,}")
        if obj.min_data_points is not None:
            parts.append(f"pts≥{obj.min_data_points}")

        if not parts:
            return format_html(
                '<span class="text-[11px] text-slate-400 italic">all products</span>'
            )

        summary = " & ".join(parts)
        if len(summary) > 80:
            summary = summary[:77] + "..."
        return format_html(
            '<span class="text-[11px] font-mono text-slate-600 dark:text-slate-400">{}</span>',
            summary,
        )

    @admin.display(description="Target", ordering="target_priority")
    def target_badge(self, obj):
        priority_colors = {
            0: "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            1: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            2: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            3: "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        }
        classes = priority_colors.get(obj.target_priority, priority_colors[3])
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-semibold {}">P{}</span>',
            classes, obj.target_priority,
        )

    @admin.display(description="Reviews")
    def reviews_badge(self, obj):
        if obj.also_mark_reviews:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">+Reviews</span>'
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Would Match")
    def preview_count_display(self, obj):
        try:
            count = obj.preview_count()
            if count > 0:
                return format_html(
                    '<span class="text-[13px] font-semibold text-amber-600 dark:text-amber-400">{}</span>',
                    f"{count:,}",
                )
            return format_html(
                '<span class="text-[12px] text-slate-400">0</span>'
            )
        except Exception:
            return format_html(
                '<span class="text-[12px] text-red-400">error</span>'
            )

    @admin.display(description="Updated", ordering="updated_at")
    def updated_ago(self, obj):
        if obj.updated_at:
            delta = timezone.now() - obj.updated_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.updated_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.updated_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    @admin.action(description="Apply selected rules now")
    def apply_selected_rules(self, request, queryset):
        total = 0
        for rule in queryset.filter(is_active=True).order_by("order"):
            qs = rule.build_queryset()
            count = qs.update(enrichment_priority=rule.target_priority)
            if rule.also_mark_reviews and count > 0:
                qs.filter(review_status="skip").update(review_status="pending")
            total += count
        self.message_user(
            request,
            f"Applied {queryset.count()} rules — {total} products updated.",
        )

    @admin.action(description="Deactivate selected rules")
    def deactivate_rules(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} rules deactivated.")

    @admin.action(description="Activate selected rules")
    def activate_rules(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} rules activated.")
