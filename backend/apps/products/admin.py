"""Enhanced product admin — data quality stats, custom filters, merge action."""
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html

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
            return queryset.filter(current_best_price__lt=5000)
        if self.value() == "5k-20k":
            return queryset.filter(current_best_price__gte=5000, current_best_price__lt=20000)
        if self.value() == "20k-50k":
            return queryset.filter(current_best_price__gte=20000, current_best_price__lt=50000)
        if self.value() == "gt50k":
            return queryset.filter(current_best_price__gte=50000)
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
class ProductAdmin(admin.ModelAdmin):
    change_list_template = "admin/products/product/change_list.html"

    list_display = [
        "title_short",
        "brand",
        "category",
        "price_display",
        "listing_count",
        "dudscore_badge",
        "has_images_icon",
        "is_lightweight_icon",
        "total_reviews",
        "status",
        "updated_at",
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
    list_per_page = 50
    list_select_related = ["brand", "category"]
    inlines = [ProductListingInline]

    actions = ["merge_selected", "mark_inactive", "trigger_dudscore_recalc"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_listing_count=Count("listings"))

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------

    @admin.display(description="Title", ordering="title")
    def title_short(self, obj):
        t = obj.title
        return t[:60] + "..." if len(t) > 60 else t

    @admin.display(description="Price", ordering="current_best_price")
    def price_display(self, obj):
        if obj.current_best_price is None:
            return "-"
        p = int(obj.current_best_price)
        # Indian numbering: 1,23,456
        s = str(p)
        if len(s) <= 3:
            formatted = s
        else:
            last3 = s[-3:]
            rest = s[:-3]
            parts = []
            while rest:
                parts.append(rest[-2:])
                rest = rest[:-2]
            formatted = ",".join(reversed(parts)) + "," + last3
        return f"₹{formatted}"

    @admin.display(description="Listings", ordering="_listing_count")
    def listing_count(self, obj):
        return obj._listing_count

    @admin.display(description="DudScore", ordering="dud_score")
    def dudscore_badge(self, obj):
        if obj.dud_score is None:
            return format_html(
                '<span style="color:#94a3b8;font-size:11px;">—</span>'
            )
        score = float(obj.dud_score)
        if score >= 80:
            bg, fg = "#f0fdf4", "#16A34A"
        elif score >= 50:
            bg, fg = "#fffbeb", "#d97706"
        else:
            bg, fg = "#fef2f2", "#DC2626"
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, fg, f"{score:.1f}",
        )

    @admin.display(description="Images", boolean=True)
    def has_images_icon(self, obj):
        return bool(obj.images)

    @admin.display(description="Lightweight", boolean=True)
    def is_lightweight_icon(self, obj):
        return obj.is_lightweight

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
# Other model admins (unchanged)
# ------------------------------------------------------------------

@admin.register(Marketplace)
class MarketplaceAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "scraper_status"]


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "parent_display", "level", "slug", "product_count", "is_active", "display_order"]
    list_filter = ["level", "is_active", "parent"]
    list_editable = ["display_order", "is_active"]
    search_fields = ["name", "slug"]
    ordering = ["level", "parent__name", "display_order", "name"]

    @admin.display(description="Hierarchy")
    def parent_display(self, obj):
        parts = []
        current = obj.parent
        while current:
            parts.append(current.name)
            current = current.parent
        return " > ".join(reversed(parts)) if parts else "—"


@admin.register(MarketplaceCategoryMapping)
class MarketplaceCategoryMappingAdmin(admin.ModelAdmin):
    list_display = ["marketplace", "marketplace_category_path", "canonical_category", "confidence", "updated_at"]
    list_filter = ["marketplace", "confidence"]
    search_fields = ["marketplace_category_path", "canonical_category__name"]
    list_editable = ["canonical_category", "confidence"]
    raw_id_fields = ["canonical_category"]
    actions = ["mark_as_reviewed"]

    @admin.action(description="Mark selected mappings as reviewed (manual)")
    def mark_as_reviewed(self, request, queryset):
        updated = queryset.update(confidence="manual")
        self.message_user(request, f"{updated} mappings marked as reviewed.")


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ["name", "slug", "verified"]
    list_filter = ["verified"]
    search_fields = ["name", "slug"]


@admin.register(ProductListing)
class ProductListingAdmin(admin.ModelAdmin):
    list_display = [
        "product_title_short", "marketplace", "price_display",
        "mrp_display", "discount_pct", "in_stock_icon", "seller",
        "match_confidence", "last_scraped_at",
    ]
    list_filter = ["marketplace", "in_stock"]
    search_fields = ["product__title", "external_id"]
    list_select_related = ["product", "marketplace", "seller"]

    @admin.display(description="Product", ordering="product__title")
    def product_title_short(self, obj):
        t = obj.product.title
        return t[:50] + "..." if len(t) > 50 else t

    @admin.display(description="Price", ordering="current_price")
    def price_display(self, obj):
        if obj.current_price is None:
            return "-"
        return f"₹{int(obj.current_price):,}"

    @admin.display(description="MRP", ordering="mrp")
    def mrp_display(self, obj):
        if obj.mrp is None:
            return "-"
        return f"₹{int(obj.mrp):,}"

    @admin.display(description="In Stock", boolean=True)
    def in_stock_icon(self, obj):
        return obj.in_stock


@admin.register(Seller)
class SellerAdmin(admin.ModelAdmin):
    list_display = ["name", "marketplace", "avg_rating", "total_ratings", "is_verified"]
    list_filter = ["marketplace", "is_verified"]
    search_fields = ["name", "external_seller_id"]


@admin.register(BankCard)
class BankCardAdmin(admin.ModelAdmin):
    list_display = ["bank_name", "card_variant", "card_type", "card_network"]
    list_filter = ["bank_slug", "card_type", "card_network"]
