"""Enhanced product admin — Apex-style badges, formatted prices, data quality stats."""
from django.contrib import admin
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.html import format_html
from django.utils.timesince import timesince

from apps.admin_tools.mixins import AuditLogMixin

from .models import (
    BankCard, Brand, Category, Marketplace, MarketplaceCategoryMapping,
    Product, ProductListing, Seller,
)


# ------------------------------------------------------------------
# Custom filters
# ------------------------------------------------------------------

class HasImagesFilter(admin.SimpleListFilter):
    title = "has images"
    parameter_name = "has_images"

    def lookups(self, request, model_admin):
        return [("yes", "Has images"), ("no", "No images")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.exclude(images__in=[None, []])
        if self.value() == "no":
            return queryset.filter(Q(images__isnull=True) | Q(images=[]))
        return queryset


class HasDudScoreFilter(admin.SimpleListFilter):
    title = "has DudScore"
    parameter_name = "has_dudscore"

    def lookups(self, request, model_admin):
        return [("yes", "Scored"), ("no", "Unscored")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(dud_score__isnull=False)
        if self.value() == "no":
            return queryset.filter(dud_score__isnull=True)
        return queryset


class IsLightweightFilter(admin.SimpleListFilter):
    title = "lightweight"
    parameter_name = "lightweight"

    def lookups(self, request, model_admin):
        return [("yes", "Lightweight only"), ("no", "Enriched only")]

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(is_lightweight=True)
        if self.value() == "no":
            return queryset.filter(is_lightweight=False)
        return queryset


class ListingCountFilter(admin.SimpleListFilter):
    title = "listing count"
    parameter_name = "listing_count"

    def lookups(self, request, model_admin):
        return [("0", "No listings"), ("1", "1 listing"), ("2+", "2+ listings")]

    def queryset(self, request, queryset):
        qs = queryset.annotate(_lc=Count("listings"))
        if self.value() == "0":
            return qs.filter(_lc=0)
        if self.value() == "1":
            return qs.filter(_lc=1)
        if self.value() == "2+":
            return qs.filter(_lc__gte=2)
        return queryset


class PriceRangeFilter(admin.SimpleListFilter):
    title = "price range"
    parameter_name = "price_range"

    def lookups(self, request, model_admin):
        return [
            ("lt5k", "< ₹5,000"),
            ("5k-20k", "₹5,000 – ₹20,000"),
            ("20k-50k", "₹20,000 – ₹50,000"),
            ("gt50k", "> ₹50,000"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "lt5k":
            return queryset.filter(current_best_price__lt=500000)
        if self.value() == "5k-20k":
            return queryset.filter(current_best_price__gte=500000, current_best_price__lt=2000000)
        if self.value() == "20k-50k":
            return queryset.filter(current_best_price__gte=2000000, current_best_price__lt=5000000)
        if self.value() == "gt50k":
            return queryset.filter(current_best_price__gte=5000000)
        return queryset


# ------------------------------------------------------------------
# Inline
# ------------------------------------------------------------------

class ProductListingInline(admin.TabularInline):
    model = ProductListing
    extra = 0
    fields = [
        "marketplace", "external_id", "current_price", "mrp",
        "discount_pct", "in_stock", "seller", "match_confidence",
        "last_scraped_at",
    ]
    readonly_fields = ["marketplace", "external_id", "last_scraped_at"]
    show_change_link = True


# ------------------------------------------------------------------
# ProductAdmin
# ------------------------------------------------------------------

@admin.register(Product)
class ProductAdmin(AuditLogMixin, admin.ModelAdmin):
    change_list_template = "admin/products/product/change_list.html"

    list_display = [
        "product_display",
        "brand_display",
        "category_display",
        "price_formatted",
        "listing_count_display",
        "dudscore_badge",
        "stock_badge",
        "lightweight_badge",
        "updated_ago",
    ]
    list_filter = [
        "status",
        "category",
        "brand",
        HasImagesFilter,
        HasDudScoreFilter,
        IsLightweightFilter,
        ListingCountFilter,
        PriceRangeFilter,
    ]
    search_fields = ["title", "slug", "brand__name", "listings__external_id"]
    readonly_fields = ["id", "created_at", "updated_at", "first_seen_at"]
    list_per_page = 30
    list_select_related = ["brand", "category"]
    inlines = [ProductListingInline]

    actions = ["merge_selected", "mark_inactive", "trigger_dudscore_recalc", "full_dudscore_recalc"]

    def get_inlines(self, request, obj=None):
        inlines = list(self.inlines)
        # DudScoreHistory is a TimescaleDB hypertable (no 'id' column).
        # Django inlines require an id PK, so skip until model gets a
        # surrogate PK or a custom inline queryset is implemented.
        return inlines

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_listing_count=Count("listings"))

    # ------------------------------------------------------------------
    # Display columns — Apex-style
    # ------------------------------------------------------------------

    @admin.display(description="Product", ordering="title")
    def product_display(self, obj):
        t = obj.title
        short = t[:55] + "..." if len(t) > 55 else t
        return format_html(
            '<div class="max-w-[350px]">'
            '  <div class="text-[13px] font-medium text-slate-800 dark:text-slate-200 truncate">{}</div>'
            '  <div class="text-[11px] text-slate-400 font-mono">{}</div>'
            '</div>',
            short, obj.slug[:40] if obj.slug else "",
        )

    @admin.display(description="Brand", ordering="brand__name")
    def brand_display(self, obj):
        if obj.brand:
            return format_html(
                '<span class="text-[13px] text-slate-700 dark:text-slate-300">{}</span>',
                obj.brand.name,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Category", ordering="category__name")
    def category_display(self, obj):
        if obj.category:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400">{}</span>',
                obj.category.name,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Price", ordering="current_best_price")
    def price_formatted(self, obj):
        if obj.current_best_price is None:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        p = int(obj.current_best_price) // 100  # paisa → rupees
        return format_html(
            '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
            f"\u20b9{p:,}",
        )

    @admin.display(description="Listings", ordering="_listing_count")
    def listing_count_display(self, obj):
        count = obj._listing_count
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                count,
            )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px]'
            ' bg-slate-100 text-slate-400 dark:bg-slate-500/20">0</span>'
        )

    @admin.display(description="DudScore", ordering="dud_score")
    def dudscore_badge(self, obj):
        if obj.dud_score is None:
            return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')
        score = float(obj.dud_score)
        if score >= 70:
            classes = "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400"
        elif score >= 40:
            classes = "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400"
        else:
            classes = "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400"
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-semibold {}">{}</span>',
            classes, f"{score:.1f}",
        )

    @admin.display(description="Status", ordering="status")
    def stock_badge(self, obj):
        status_colors = {
            "active": ("bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400", "Active"),
            "discontinued": ("bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400", "Discontinued"),
            "pending": ("bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400", "Pending"),
        }
        classes, label = status_colors.get(
            obj.status,
            ("bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400", obj.status),
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, label,
        )

    @admin.display(description="Type")
    def lightweight_badge(self, obj):
        if obj.is_lightweight:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
                ' bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400">Lightweight</span>'
            )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium'
            ' bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400">Enriched</span>'
        )

    @admin.display(description="Updated")
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
    # Admin actions
    # ------------------------------------------------------------------

    @admin.action(description="Merge selected → first product (move listings)")
    def merge_selected(self, request, queryset):
        products = list(queryset.order_by("created_at"))
        if len(products) < 2:
            self.message_user(request, "Select at least 2 products to merge.", level="error")
            return
        target = products[0]
        sources = products[1:]
        moved = 0
        for src in sources:
            moved += src.listings.update(product=target)
            src.merged_into = target
            src.status = Product.Status.DISCONTINUED
            src.save(update_fields=["merged_into", "status", "updated_at"])
        self.message_user(
            request,
            f"Merged {len(sources)} products into '{target.title[:50]}'. "
            f"Moved {moved} listings.",
        )

    @admin.action(description="Mark as inactive")
    def mark_inactive(self, request, queryset):
        updated = queryset.update(status=Product.Status.DISCONTINUED)
        self.message_user(request, f"{updated} products marked inactive.")

    @admin.action(description="Trigger DudScore recalculation")
    def trigger_dudscore_recalc(self, request, queryset):
        from django.contrib import messages

        try:
            from apps.scoring.tasks import compute_dudscore
            count = 0
            for product in queryset:
                compute_dudscore.delay(str(product.id))
                count += 1
            messages.success(request, f"DudScore recalculation queued for {count} products.")
        except ImportError:
            messages.warning(request, "scoring.tasks.compute_dudscore not available yet.")
        except Exception as e:
            messages.error(request, f"Failed to queue recalculation: {e}")

    @admin.action(description="Full DudScore recalculation (ALL products)")
    def full_dudscore_recalc(self, request, queryset):
        from django.contrib import messages

        try:
            from apps.scoring.tasks import full_dudscore_recalculation
            result = full_dudscore_recalculation.delay()
            messages.success(
                request,
                f"Full DudScore recalculation queued. Task: {result.id}",
            )
        except ImportError:
            messages.warning(request, "scoring.tasks.full_dudscore_recalculation not available yet.")
        except Exception as e:
            messages.error(request, f"Failed to queue full recalculation: {e}")

    # ------------------------------------------------------------------
    # Stats header
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        total = Product.objects.count()
        active = Product.objects.filter(status=Product.Status.ACTIVE).count()
        lightweight = Product.objects.filter(is_lightweight=True).count()
        enriched = Product.objects.filter(is_lightweight=False).count()

        missing_images = Product.objects.filter(
            Q(images__isnull=True) | Q(images=[])
        ).count()
        missing_brand = Product.objects.filter(brand__isnull=True).count()
        missing_category = Product.objects.filter(category__isnull=True).count()
        unscored = Product.objects.filter(dud_score__isnull=True).count()
        no_listings = Product.objects.annotate(_lc=Count("listings")).filter(_lc=0).count()

        extra_context.update({
            "stats_header": True,
            "total_products": total,
            "active_products": active,
            "lightweight_products": lightweight,
            "enriched_products": enriched,
            "missing_images": missing_images,
            "missing_brand": missing_brand,
            "missing_category": missing_category,
            "unscored_products": unscored,
            "no_listings": no_listings,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ------------------------------------------------------------------
# Other model admins — Apex-style
# ------------------------------------------------------------------

@admin.register(Marketplace)
class MarketplaceAdmin(AuditLogMixin, admin.ModelAdmin):
    list_display = ["name_display", "slug", "scraper_status_badge"]
    list_per_page = 30

    @admin.display(description="Name", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name,
        )

    @admin.display(description="Status", ordering="scraper_status")
    def scraper_status_badge(self, obj):
        status = obj.scraper_status or "\u2014"
        status_colors = {
            "active": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "paused": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "disabled": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "error": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
        }
        classes = status_colors.get(
            status.lower() if status != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            classes, status.title() if status != "\u2014" else status,
        )


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = [
        "name_display", "parent_display", "level_badge",
        "slug", "product_count_badge", "active_badge", "display_order",
    ]
    list_filter = ["level", "is_active", "parent"]
    list_editable = ["display_order"]
    search_fields = ["name", "slug"]
    ordering = ["level", "parent__name", "display_order", "name"]
    list_per_page = 30

    @admin.display(description="Name", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name,
        )

    @admin.display(description="Hierarchy")
    def parent_display(self, obj):
        parts = []
        current = obj.parent
        while current:
            parts.append(current.name)
            current = current.parent
        if parts:
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                " > ".join(reversed(parts)),
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Level", ordering="level")
    def level_badge(self, obj):
        level_colors = {
            0: "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            1: "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            2: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            3: "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
        }
        classes = level_colors.get(
            obj.level, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400"
        )
        return format_html(
            '<span class="inline-flex px-2.5 py-1 rounded-md text-[11px] font-semibold {}">L{}</span>',
            classes, obj.level,
        )

    @admin.display(description="Products", ordering="product_count")
    def product_count_badge(self, obj):
        count = obj.product_count or 0
        if count > 0:
            return format_html(
                '<span class="inline-flex px-2 py-0.5 rounded-full text-[11px] font-semibold'
                ' bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400">{}</span>',
                f"{count:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">0</span>')

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


@admin.register(MarketplaceCategoryMapping)
class MarketplaceCategoryMappingAdmin(admin.ModelAdmin):
    list_display = [
        "marketplace_badge", "category_path_display",
        "canonical_display", "confidence_badge", "updated_ago",
    ]
    list_filter = ["marketplace", "confidence"]
    search_fields = ["marketplace_category_path", "canonical_category__name"]
    raw_id_fields = ["canonical_category"]
    list_select_related = ["marketplace", "canonical_category"]
    list_per_page = 30
    actions = ["mark_as_reviewed"]

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

    @admin.display(description="Marketplace Category")
    def category_path_display(self, obj):
        path = obj.marketplace_category_path or "\u2014"
        short = path[:60] + "..." if len(path) > 60 else path
        return format_html(
            '<span class="text-[12px] text-slate-600 dark:text-slate-400">{}</span>',
            short,
        )

    @admin.display(description="Canonical", ordering="canonical_category__name")
    def canonical_display(self, obj):
        if obj.canonical_category:
            return format_html(
                '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
                obj.canonical_category.name,
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Confidence", ordering="confidence")
    def confidence_badge(self, obj):
        conf = obj.confidence or "\u2014"
        conf_colors = {
            "manual": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "auto": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "unreviewed": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
        }
        color = conf_colors.get(
            conf.lower() if conf != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, conf.title() if conf != "\u2014" else conf,
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

    @admin.action(description="Mark selected mappings as reviewed (manual)")
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(confidence="manual")
        self.message_user(request, f"{updated} mappings marked as reviewed.")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name_display", "slug", "verified_badge"]
    list_filter = ["verified"]
    search_fields = ["name", "slug"]
    list_per_page = 30

    @admin.display(description="Name", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name,
        )

    @admin.display(description="Verified", ordering="verified")
    def verified_badge(self, obj):
        if obj.verified:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Verified</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>'
            '<span class="text-slate-400">Unverified</span></span>'
        )


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = [
        "product_title_display",
        "marketplace_badge",
        "price_display",
        "mrp_display",
        "stock_badge",
        "rating_display",
        "scraped_ago",
    ]
    list_filter = ["marketplace", "in_stock"]
    search_fields = ["product__title", "external_id"]
    list_select_related = ["product", "marketplace", "seller"]
    list_per_page = 30

    @admin.display(description="Product", ordering="product__title")
    def product_title_display(self, obj):
        t = obj.product.title
        short = t[:55] + "..." if len(t) > 55 else t
        return format_html(
            '<div class="max-w-[350px]">'
            '  <div class="text-[13px] font-medium text-slate-800 dark:text-slate-200 truncate">{}</div>'
            '  <div class="text-[11px] text-slate-400 font-mono">{}</div>'
            '</div>',
            short, obj.external_id or "\u2014",
        )

    @admin.display(description="Marketplace", ordering="marketplace__name")
    def marketplace_badge(self, obj):
        name = obj.marketplace.name if obj.marketplace else "\u2014"
        colors = {
            "Amazon.in": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "Amazon India": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
            "Flipkart": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "Myntra": "bg-pink-100 text-pink-700 dark:bg-pink-500/20 dark:text-pink-400",
            "Croma": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "Ajio": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "Tata CLiQ": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = colors.get(name, "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400")
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, name,
        )

    @admin.display(description="Price", ordering="current_price")
    def price_display(self, obj):
        if obj.current_price is not None:
            p = int(obj.current_price) // 100
            return format_html(
                '<span class="text-[13px] font-semibold text-slate-800 dark:text-slate-200">{}</span>',
                f"\u20b9{p:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="MRP", ordering="mrp")
    def mrp_display(self, obj):
        if obj.mrp and obj.current_price and obj.mrp > obj.current_price:
            m = int(obj.mrp) // 100
            return format_html(
                '<span class="text-[12px] text-slate-400 line-through">{}</span>',
                f"\u20b9{m:,}",
            )
        if obj.mrp:
            m = int(obj.mrp) // 100
            return format_html(
                '<span class="text-[12px] text-slate-500">{}</span>',
                f"\u20b9{m:,}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Stock", ordering="in_stock")
    def stock_badge(self, obj):
        if obj.in_stock:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400">In Stock</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-red-500"></span>'
            '<span class="text-red-600 dark:text-red-400">Out of Stock</span></span>'
        )

    @admin.display(description="Rating", ordering="rating")
    def rating_display(self, obj):
        if obj.rating:
            return format_html(
                '<span class="text-[12px]">'
                '<span class="text-amber-500">\u2605</span> '
                '<span class="font-medium text-slate-700 dark:text-slate-300">{}</span>'
                '<span class="text-slate-400 ml-1">({})</span></span>',
                f"{float(obj.rating):.1f}", f"{obj.review_count:,}" if obj.review_count else "0",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Last Scraped", ordering="last_scraped_at")
    def scraped_ago(self, obj):
        if obj.last_scraped_at:
            delta = timezone.now() - obj.last_scraped_at
            if delta.days > 30:
                return format_html(
                    '<span class="text-[12px] text-slate-400">{}</span>',
                    timezone.localtime(obj.last_scraped_at).strftime("%b %d, %Y"),
                )
            return format_html(
                '<span class="text-[12px] text-slate-500">{} ago</span>',
                timesince(obj.last_scraped_at, timezone.now()).split(",")[0],
            )
        return format_html('<span class="text-[12px] text-slate-400">Never</span>')


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ["name_display", "marketplace_badge", "rating_display", "total_ratings", "verified_badge"]
    list_filter = ["marketplace", "is_verified"]
    search_fields = ["name", "external_seller_id"]
    list_select_related = ["marketplace"]
    list_per_page = 30

    @admin.display(description="Seller", ordering="name")
    def name_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.name[:50],
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

    @admin.display(description="Rating", ordering="avg_rating")
    def rating_display(self, obj):
        if obj.avg_rating:
            return format_html(
                '<span class="text-[12px]">'
                '<span class="text-amber-500">\u2605</span> '
                '<span class="font-medium text-slate-700 dark:text-slate-300">{}</span></span>',
                f"{float(obj.avg_rating):.1f}",
            )
        return format_html('<span class="text-[12px] text-slate-400">&mdash;</span>')

    @admin.display(description="Verified", ordering="is_verified")
    def verified_badge(self, obj):
        if obj.is_verified:
            return format_html(
                '<span class="inline-flex items-center gap-1 text-[12px]">'
                '<span class="w-2 h-2 rounded-full bg-emerald-500"></span>'
                '<span class="text-emerald-600 dark:text-emerald-400 font-medium">Verified</span></span>'
            )
        return format_html(
            '<span class="inline-flex items-center gap-1 text-[12px]">'
            '<span class="w-2 h-2 rounded-full bg-slate-300 dark:bg-slate-600"></span>'
            '<span class="text-slate-400">Unverified</span></span>'
        )


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ["bank_display", "card_variant", "type_badge", "network_badge"]
    list_filter = ["bank_slug", "card_type", "card_network"]
    search_fields = ["bank_name", "card_variant"]
    list_per_page = 30

    @admin.display(description="Bank", ordering="bank_name")
    def bank_display(self, obj):
        return format_html(
            '<span class="text-[13px] font-medium text-slate-800 dark:text-slate-200">{}</span>',
            obj.bank_name,
        )

    @admin.display(description="Type", ordering="card_type")
    def type_badge(self, obj):
        ct = obj.card_type or "\u2014"
        type_colors = {
            "credit": "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-400",
            "debit": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "prepaid": "bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-400",
        }
        color = type_colors.get(
            ct.lower() if ct != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, ct.title() if ct != "\u2014" else ct,
        )

    @admin.display(description="Network", ordering="card_network")
    def network_badge(self, obj):
        network = obj.card_network or "\u2014"
        network_colors = {
            "visa": "bg-blue-100 text-blue-700 dark:bg-blue-500/20 dark:text-blue-400",
            "mastercard": "bg-red-100 text-red-700 dark:bg-red-500/20 dark:text-red-400",
            "rupay": "bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-400",
            "amex": "bg-cyan-100 text-cyan-700 dark:bg-cyan-500/20 dark:text-cyan-400",
        }
        color = network_colors.get(
            network.lower() if network != "\u2014" else "",
            "bg-slate-100 text-slate-600 dark:bg-slate-500/20 dark:text-slate-400",
        )
        return format_html(
            '<span class="inline-flex px-2 py-0.5 rounded-md text-[11px] font-medium {}">{}</span>',
            color, network.title() if network != "\u2014" else network,
        )
