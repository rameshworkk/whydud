"""Enhanced pricing admin — click tracking, price alerts, backfill management."""
from datetime import timedelta

from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html

from apps.admin_tools.mixins import AuditLogMixin

from .models import BackfillProduct, ClickEvent, MarketplaceOffer, PriceAlert


# ------------------------------------------------------------------
# ClickEventAdmin
# ------------------------------------------------------------------

@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    change_list_template = "admin/pricing/clickevent/change_list.html"

    list_display = [
        "product_title",
        "marketplace",
        "source_page",
        "price_display",
        "affiliate_tag",
        "purchase_icon",
        "device_type",
        "clicked_at",
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
    list_per_page = 50
    list_select_related = ["product", "marketplace"]
    raw_id_fields = ["product", "listing", "user", "marketplace"]
    date_hierarchy = "clicked_at"

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        return t[:50] + "..." if len(t) > 50 else t

    @admin.display(description="Price", ordering="price_at_click")
    def price_display(self, obj):
        if obj.price_at_click is None:
            return "-"
        return f"₹{int(obj.price_at_click):,}"

    @admin.display(description="Purchased", boolean=True)
    def purchase_icon(self, obj):
        return obj.purchase_confirmed

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
        "user_email",
        "product_title",
        "target_price_display",
        "current_price_display",
        "marketplace",
        "is_active_icon",
        "is_triggered_icon",
        "triggered_at",
    ]
    list_filter = ["is_active", "is_triggered", "marketplace"]
    search_fields = ["user__email", "product__title"]
    readonly_fields = [
        "id", "created_at", "updated_at",
        "triggered_at", "triggered_price", "triggered_marketplace",
    ]
    list_select_related = ["user", "product", "marketplace"]
    raw_id_fields = ["user", "product"]
    list_per_page = 50

    @admin.display(description="User", ordering="user__email")
    def user_email(self, obj):
        return obj.user.email

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        return t[:40] + "..." if len(t) > 40 else t

    @admin.display(description="Target", ordering="target_price")
    def target_price_display(self, obj):
        return f"₹{int(obj.target_price):,}"

    @admin.display(description="Current", ordering="current_price")
    def current_price_display(self, obj):
        if obj.current_price is None:
            return "-"
        return f"₹{int(obj.current_price):,}"

    @admin.display(description="Active", boolean=True)
    def is_active_icon(self, obj):
        return obj.is_active

    @admin.display(description="Triggered", boolean=True)
    def is_triggered_icon(self, obj):
        return obj.is_triggered


# ------------------------------------------------------------------
# Existing model admins
# ------------------------------------------------------------------

@admin.register(MarketplaceOffer)
class MarketplaceOfferAdmin(admin.ModelAdmin):
    list_display = ["title", "marketplace", "offer_type", "bank_slug", "is_active", "valid_until"]
    list_filter = ["is_active", "offer_type", "marketplace"]
    search_fields = ["title", "bank_slug"]


@admin.register(BackfillProduct)
class BackfillProductAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = [
        "external_id", "marketplace_slug", "title", "status",
        "scrape_status", "enrichment_priority", "enrichment_method",
        "review_status", "price_data_points", "cached_points", "created_at",
    ]
    list_filter = [
        "status", "scrape_status", "enrichment_priority",
        "enrichment_method", "review_status", "marketplace_slug",
    ]
    search_fields = ["external_id", "title", "ph_code"]
    readonly_fields = ["id", "created_at", "updated_at", "cached_points", "raw_price_data"]
    actions = ["mark_for_reviews"]

    @admin.display(description="Cached Pts")
    def cached_points(self, obj):
        return len(obj.raw_price_data) if obj.raw_price_data else 0

    @admin.action(description="Mark for review scraping")
    def mark_for_reviews(self, request, queryset):
        updated = queryset.filter(scrape_status="scraped").update(review_status="pending")
        self.message_user(request, f"{updated} products marked for review scraping.")
