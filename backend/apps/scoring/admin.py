"""Enhanced scoring admin — DudScore config with audit log, history viewer."""
from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html

from .models import BrandTrustScore, DudScoreConfig, DudScoreHistory


# ------------------------------------------------------------------
# DudScoreConfigAdmin
# ------------------------------------------------------------------

@admin.register(DudScoreConfig)
class DudScoreConfigAdmin(admin.ModelAdmin):
    list_display = [
        "version",
        "is_active_icon",
        "w_sentiment",
        "w_rating_quality",
        "w_price_value",
        "w_review_credibility",
        "w_price_stability",
        "w_return_signal",
        "anomaly_spike_threshold",
        "change_reason_short",
        "created_at",
    ]
    list_filter = ["is_active"]
    readonly_fields = ["version", "activated_at", "created_at"]
    ordering = ["-version"]

    fieldsets = (
        (None, {"fields": ("version", "is_active", "activated_at", "change_reason")}),
        ("Weights", {"fields": (
            "w_sentiment", "w_rating_quality", "w_price_value",
            "w_review_credibility", "w_price_stability", "w_return_signal",
        )}),
        ("Thresholds", {"fields": (
            "fraud_penalty_threshold", "min_review_threshold",
            "cold_start_penalty", "anomaly_spike_threshold",
        )}),
        ("Meta", {"fields": ("created_by", "created_at")}),
    )

    @admin.display(description="Active", boolean=True)
    def is_active_icon(self, obj):
        return obj.is_active

    @admin.display(description="Reason")
    def change_reason_short(self, obj):
        r = obj.change_reason or ""
        return r[:60] + "..." if len(r) > 60 else r

    def save_model(self, request, obj, form, change):
        old_values = {}
        if change:
            # Capture old values for audit log
            try:
                old = DudScoreConfig.objects.get(pk=obj.pk)
                weight_fields = [
                    "w_sentiment", "w_rating_quality", "w_price_value",
                    "w_review_credibility", "w_price_stability", "w_return_signal",
                    "fraud_penalty_threshold", "min_review_threshold",
                    "cold_start_penalty", "anomaly_spike_threshold", "is_active",
                ]
                for f in weight_fields:
                    old_val = getattr(old, f)
                    new_val = getattr(obj, f)
                    if old_val != new_val:
                        old_values[f] = str(old_val)
            except DudScoreConfig.DoesNotExist:
                pass

        # Enforce only 1 active config
        if obj.is_active:
            DudScoreConfig.objects.exclude(pk=obj.pk).filter(is_active=True).update(
                is_active=False
            )
            if not obj.activated_at:
                obj.activated_at = timezone.now()

        obj.created_by = request.user.id
        super().save_model(request, obj, form, change)

        # Create audit log
        if old_values:
            new_values = {}
            for f in old_values:
                new_values[f] = str(getattr(obj, f))
            try:
                from apps.admin_tools.models import AuditLog
                AuditLog.objects.create(
                    admin_user=request.user,
                    action=AuditLog.Action.CONFIG_CHANGE,
                    target_type="scoring.DudScoreConfig",
                    target_id=str(obj.pk),
                    old_value=old_values,
                    new_value=new_values,
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
            except Exception:
                pass  # Don't block save if audit log fails


# ------------------------------------------------------------------
# DudScoreHistoryAdmin
# ------------------------------------------------------------------

@admin.register(DudScoreHistory)
class DudScoreHistoryAdmin(admin.ModelAdmin):
    list_display = [
        "product_title",
        "score_badge",
        "config_version",
        "time",
    ]
    list_filter = ["config_version"]
    search_fields = ["product__title"]
    readonly_fields = [
        "time", "product", "score", "config_version", "component_scores",
    ]
    list_select_related = ["product"]
    ordering = ["-time"]
    list_per_page = 50

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        return t[:50] + "..." if len(t) > 50 else t

    @admin.display(description="Score", ordering="score")
    def score_badge(self, obj):
        score = float(obj.score)
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


# ------------------------------------------------------------------
# DudScoreHistory inline for ProductAdmin
# ------------------------------------------------------------------

class DudScoreHistoryInline(admin.TabularInline):
    model = DudScoreHistory
    extra = 0
    max_num = 10
    fields = ["time", "score", "config_version", "component_scores"]
    readonly_fields = ["time", "score", "config_version", "component_scores"]
    ordering = ["-time"]
    verbose_name = "DudScore History"
    verbose_name_plural = "DudScore History (last 10)"

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# ------------------------------------------------------------------
# BrandTrustScoreAdmin
# ------------------------------------------------------------------

@admin.register(BrandTrustScore)
class BrandTrustScoreAdmin(admin.ModelAdmin):
    list_display = [
        "brand", "avg_dud_score", "product_count",
        "trust_tier_badge", "avg_fake_review_pct",
        "quality_consistency", "computed_at",
    ]
    list_filter = ["trust_tier"]
    search_fields = ["brand__name", "brand__slug"]
    readonly_fields = ["computed_at", "created_at", "updated_at"]

    @admin.display(description="Trust Tier", ordering="trust_tier")
    def trust_tier_badge(self, obj):
        colors = {
            "excellent": ("#f0fdf4", "#16A34A"),
            "good": ("#f0fdf4", "#22c55e"),
            "average": ("#fffbeb", "#d97706"),
            "poor": ("#fef2f2", "#ea580c"),
            "avoid": ("#fef2f2", "#DC2626"),
        }
        bg, fg = colors.get(obj.trust_tier, ("#f8fafc", "#64748b"))
        return format_html(
            '<span style="background:{};color:{};padding:2px 8px;border-radius:10px;'
            'font-size:11px;font-weight:600;">{}</span>',
            bg, fg, obj.get_trust_tier_display(),
        )
