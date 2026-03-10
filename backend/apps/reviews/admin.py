"""Enhanced review admin — moderation stats, credibility badges, fraud detection actions."""
from datetime import timedelta

from django.contrib import admin
from django.db.models import Avg, Count, Q
from django.utils import timezone
from django.utils.html import format_html

from apps.admin_tools.mixins import AuditLogMixin

from .models import Review, ReviewerProfile, ReviewVote


# ------------------------------------------------------------------
# Custom filters
# ------------------------------------------------------------------

class CredibilityRangeFilter(admin.SimpleListFilter):
    title = "credibility"
    parameter_name = "credibility"

    def lookups(self, request, model_admin):
        return [
            ("low", "Low (< 0.3)"),
            ("medium", "Medium (0.3 – 0.7)"),
            ("high", "High (> 0.7)"),
            ("none", "Unscored"),
        ]

    def queryset(self, request, queryset):
        if self.value() == "low":
            return queryset.filter(credibility_score__lt=0.3)
        if self.value() == "medium":
            return queryset.filter(credibility_score__gte=0.3, credibility_score__lte=0.7)
        if self.value() == "high":
            return queryset.filter(credibility_score__gt=0.7)
        if self.value() == "none":
            return queryset.filter(credibility_score__isnull=True)
        return queryset


# ------------------------------------------------------------------
# ReviewAdmin
# ------------------------------------------------------------------

@admin.register(Review)
class ReviewAdmin(AuditLogMixin, admin.ModelAdmin):
    change_list_template = "admin/reviews/review/change_list.html"

    list_display = [
        "product_title",
        "reviewer_name",
        "rating_stars",
        "credibility_badge",
        "source",
        "is_published_icon",
        "is_flagged_icon",
        "fraud_flags_summary",
        "helpful_vote_count",
        "created_at",
    ]
    list_filter = [
        "is_published",
        "is_flagged",
        "source",
        "rating",
        CredibilityRangeFilter,
    ]
    search_fields = ["body", "body_positive", "body_negative", "product__title"]
    readonly_fields = ["id", "content_hash", "created_at", "updated_at"]
    list_per_page = 50
    list_select_related = ["product"]
    raw_id_fields = ["product", "listing", "user"]

    actions = [
        "approve_and_publish",
        "reject_reviews",
        "rerun_fraud_detection",
        "suspend_reviewer",
    ]

    # ------------------------------------------------------------------
    # Display columns
    # ------------------------------------------------------------------

    @admin.display(description="Product", ordering="product__title")
    def product_title(self, obj):
        t = obj.product.title
        return t[:40] + "..." if len(t) > 40 else t

    @admin.display(description="Rating", ordering="rating")
    def rating_stars(self, obj):
        filled = int(obj.rating) if obj.rating else 0
        empty = 5 - filled
        return format_html(
            '<span style="color:#FBBF24;font-size:14px;letter-spacing:-1px;">{}</span>'
            '<span style="color:#cbd5e1;font-size:14px;letter-spacing:-1px;">{}</span>',
            "\u2605" * filled,
            "\u2606" * empty,
        )

    @admin.display(description="Credibility", ordering="credibility_score")
    def credibility_badge(self, obj):
        if obj.credibility_score is None:
            return format_html('<span style="color:#94a3b8;font-size:11px;">\u2014</span>')
        score = float(obj.credibility_score)
        if score > 0.7:
            color = "#16A34A"
            icon = "\U0001f7e2"
        elif score >= 0.3:
            color = "#d97706"
            icon = "\U0001f7e1"
        else:
            color = "#DC2626"
            icon = "\U0001f534"
        return format_html(
            '<span style="font-size:12px;">{}</span> '
            '<span style="color:{};font-size:11px;font-weight:600;">{}</span>',
            icon, color, f"{score:.2f}",
        )

    @admin.display(description="Published", boolean=True)
    def is_published_icon(self, obj):
        return obj.is_published

    @admin.display(description="Flagged", boolean=True)
    def is_flagged_icon(self, obj):
        return obj.is_flagged

    @admin.display(description="Fraud Flags")
    def fraud_flags_summary(self, obj):
        if not obj.fraud_flags:
            return "-"
        flags = obj.fraud_flags
        if isinstance(flags, list):
            count = len(flags)
            summary = ", ".join(str(f)[:20] for f in flags[:3])
        elif isinstance(flags, dict):
            count = len(flags)
            summary = ", ".join(list(flags.keys())[:3])
        else:
            return "-"
        if count == 0:
            return "-"
        return format_html(
            '<span style="color:#DC2626;font-size:11px;" title="{}">'
            '\u26a0\ufe0f {} flag{}</span>',
            summary, count, "s" if count != 1 else "",
        )

    # ------------------------------------------------------------------
    # Admin actions
    # ------------------------------------------------------------------

    @admin.action(description="Approve & publish now")
    def approve_and_publish(self, request, queryset):
        updated = queryset.update(is_published=True, is_flagged=False)
        self.message_user(request, f"{updated} reviews approved and published.")

    @admin.action(description="Reject selected reviews")
    def reject_reviews(self, request, queryset):
        count = queryset.count()
        # Create audit log entries before deleting
        try:
            from apps.admin_tools.models import AuditLog
            for review in queryset:
                AuditLog.objects.create(
                    admin_user=request.user,
                    action=AuditLog.Action.REJECT,
                    target_type="reviews.Review",
                    target_id=str(review.id),
                    old_value={
                        "product_id": str(review.product_id),
                        "rating": review.rating,
                        "reviewer_name": review.reviewer_name,
                    },
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
        except Exception:
            pass  # Don't block rejection if audit log fails
        queryset.delete()
        self.message_user(request, f"{count} reviews rejected and deleted.")

    @admin.action(description="Re-run fraud detection")
    def rerun_fraud_detection(self, request, queryset):
        from django.contrib import messages
        try:
            from apps.reviews.tasks import detect_fake_reviews
            product_ids = set(queryset.values_list("product_id", flat=True))
            for pid in product_ids:
                detect_fake_reviews.delay(str(pid))
            messages.success(
                request,
                f"Fraud detection queued for {len(product_ids)} products "
                f"({queryset.count()} reviews selected).",
            )
        except ImportError:
            messages.warning(request, "reviews.tasks.detect_fake_reviews not available yet.")
        except Exception as e:
            messages.error(request, f"Failed to queue fraud detection: {e}")

    @admin.action(description="Suspend reviewer (deactivate + hide reviews)")
    def suspend_reviewer(self, request, queryset):
        from django.contrib import messages
        user_ids = set(
            queryset.exclude(user__isnull=True).values_list("user_id", flat=True)
        )
        if not user_ids:
            messages.warning(request, "No reviews with linked users found.")
            return
        from apps.accounts.models import User
        suspended = User.objects.filter(id__in=user_ids).update(is_active=False)
        hidden = Review.objects.filter(user_id__in=user_ids).update(is_published=False)
        # Audit log
        try:
            from apps.admin_tools.models import AuditLog
            for uid in user_ids:
                AuditLog.objects.create(
                    admin_user=request.user,
                    action=AuditLog.Action.SUSPEND,
                    target_type="accounts.User",
                    target_id=str(uid),
                    ip_address=request.META.get("REMOTE_ADDR"),
                )
        except Exception:
            pass
        messages.success(
            request,
            f"Suspended {suspended} users, hid {hidden} reviews.",
        )

    # ------------------------------------------------------------------
    # Stats header
    # ------------------------------------------------------------------

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        hold_cutoff = now - timedelta(hours=48)

        # Pending = unpublished reviews created in last 48h (on hold)
        pending_count = Review.objects.filter(
            is_published=False, created_at__gte=hold_cutoff,
        ).count()
        flagged_count = Review.objects.filter(is_flagged=True).count()
        published_today = Review.objects.filter(
            is_published=True, created_at__gte=today,
        ).count()

        avg_credibility = Review.objects.filter(
            credibility_score__isnull=False,
        ).aggregate(avg=Avg("credibility_score"))["avg"]

        total_reviews = Review.objects.count()
        flagged_total = Review.objects.filter(is_flagged=True).count()
        fraud_rate = round(flagged_total / total_reviews * 100, 1) if total_reviews else 0

        extra_context.update({
            "stats_header": True,
            "pending_count": pending_count,
            "flagged_count": flagged_count,
            "published_today": published_today,
            "avg_credibility": f"{avg_credibility:.2f}" if avg_credibility else "N/A",
            "fraud_rate": fraud_rate,
            "total_reviews": total_reviews,
        })

        return super().changelist_view(request, extra_context=extra_context)


# ------------------------------------------------------------------
# ReviewerProfileAdmin
# ------------------------------------------------------------------

@admin.register(ReviewerProfile)
class ReviewerProfileAdmin(admin.ModelAdmin):
    list_display = [
        "user", "total_reviews", "total_upvotes_received",
        "review_quality_avg", "reviewer_level", "is_top_reviewer",
    ]
    list_filter = ["reviewer_level", "is_top_reviewer"]
    search_fields = ["user__email", "user__name"]
    readonly_fields = ["created_at", "updated_at"]
