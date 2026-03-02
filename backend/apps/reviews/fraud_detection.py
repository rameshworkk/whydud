"""Rule-based fake review detection for v1.

Detects fraudulent or low-quality reviews using 5 heuristic signals:
  1. Copy-paste / duplicate content (via content_hash)
  2. Rating bursts (many same-rating reviews in a short window)
  3. Suspiciously short 5-star reviews
  4. Reviewer account patterns (new account, only 5-star, single brand)
  5. Unverified purchase with 5-star rating

Each signal produces a flag in the ``fraud_flags`` JSONField on the Review.
A credibility score (0.00–1.00) is computed based on the number and severity
of flags. Reviews with ``flag_threshold`` or more signals are auto-flagged.

All tuneable values come from ``common.app_settings.FraudDetectionConfig``.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q
from django.utils import timezone

from common.app_settings import FraudDetectionConfig

logger = logging.getLogger(__name__)


def detect_fake_reviews(product_id: str) -> dict:
    """Run all fraud detection rules on reviews for a product.

    Args:
        product_id: UUID of the product to analyse.

    Returns:
        Summary dict: ``{total, flagged, updated}`` counts.
    """
    from .models import Review

    reviews = Review.objects.filter(
        product_id=product_id,
        is_published=True,
    ).select_related("user")

    total = reviews.count()
    if total == 0:
        return {"total": 0, "flagged": 0, "updated": 0}

    # Pre-compute data shared across rules
    content_hash_counts = _content_hash_counts(reviews)
    burst_windows = _burst_windows(reviews)

    flag_threshold = FraudDetectionConfig.flag_threshold()
    updated = 0
    flagged = 0

    for review in reviews.iterator(chunk_size=500):
        fraud_flags: dict[str, bool] = {}

        # Rule 1: Copy-paste detection
        if _is_duplicate_content(review, content_hash_counts):
            fraud_flags["copy_paste"] = True

        # Rule 2: Rating burst (N+ reviews same rating in window)
        if _is_rating_burst(review, burst_windows):
            fraud_flags["rating_burst"] = True

        # Rule 3: Suspiciously short review with 5-star
        if _is_suspiciously_short(review):
            fraud_flags["suspiciously_short"] = True

        # Rule 4: Reviewer account patterns
        if _has_suspicious_reviewer_pattern(review):
            fraud_flags["suspicious_reviewer"] = True

        # Rule 5: Unverified purchase with 5-star
        if _is_unverified_5star(review):
            fraud_flags["unverified_5star"] = True

        credibility = _calculate_credibility(review, fraud_flags)
        is_flagged = len(fraud_flags) >= flag_threshold

        review.fraud_flags = fraud_flags
        review.credibility_score = credibility
        review.is_flagged = is_flagged
        review.save(update_fields=["fraud_flags", "credibility_score", "is_flagged"])

        updated += 1
        if is_flagged:
            flagged += 1

    logger.info(
        "detect_fake_reviews product=%s total=%d flagged=%d",
        product_id,
        total,
        flagged,
    )
    return {"total": total, "flagged": flagged, "updated": updated}


# ---------------------------------------------------------------------------
# Pre-computation helpers (run once per product, shared across reviews)
# ---------------------------------------------------------------------------


def _content_hash_counts(reviews) -> dict[str, int]:
    """Count occurrences of each non-empty content_hash for the review set."""
    return dict(
        reviews.exclude(content_hash="")
        .values_list("content_hash")
        .annotate(cnt=Count("id"))
        .filter(cnt__gt=1)
        .values_list("content_hash", "cnt")
    )


def _burst_windows(reviews) -> dict[tuple[int, str], int]:
    """Build a mapping of (rating, date_str) → count for burst detection.

    Groups reviews by (rating, date truncated to calendar day) so we can
    cheaply check whether a review falls inside a burst window.
    """
    from django.db.models.functions import TruncDate

    rows = (
        reviews.annotate(day=TruncDate("created_at"))
        .values("rating", "day")
        .annotate(cnt=Count("id"))
    )
    return {(r["rating"], str(r["day"])): r["cnt"] for r in rows}


# ---------------------------------------------------------------------------
# Individual rule checks
# ---------------------------------------------------------------------------


def _is_duplicate_content(review, content_hash_counts: dict[str, int]) -> bool:
    """Rule 1: Review body is a duplicate of another review (same content_hash)."""
    if not review.content_hash:
        return False
    duplicate_threshold = FraudDetectionConfig.duplicate_count_threshold()
    count = content_hash_counts.get(review.content_hash, 0)
    return count >= duplicate_threshold


def _is_rating_burst(review, burst_windows: dict[tuple[int, str], int]) -> bool:
    """Rule 2: Too many reviews with the same rating posted on the same day."""
    day_str = str(review.created_at.date()) if review.created_at else None
    if not day_str:
        return False
    burst_threshold = FraudDetectionConfig.burst_count_threshold()
    count = burst_windows.get((review.rating, day_str), 0)
    return count >= burst_threshold


def _is_suspiciously_short(review) -> bool:
    """Rule 3: Very short review body with a 5-star rating."""
    max_chars = FraudDetectionConfig.short_review_max_chars()
    body = review.body or ""
    return len(body.strip()) < max_chars and review.rating == 5


def _has_suspicious_reviewer_pattern(review) -> bool:
    """Rule 4: Reviewer account looks fake (new account, only 5-star, single brand).

    Only applies to Whydud-native reviews (scraped reviews lack user context).
    Checks:
      - Account created within the last N days AND
      - All of the user's published reviews are 5-star AND on the same brand.
    """
    if not review.user_id:
        return False

    from .models import Review

    new_account_days = FraudDetectionConfig.new_account_days()
    cutoff = timezone.now() - timedelta(days=new_account_days)

    # Check if user account is recent
    user = review.user
    if not user or not hasattr(user, "date_joined"):
        return False
    if user.date_joined > cutoff:
        # New account — check if all reviews are 5-star single brand
        user_reviews = Review.objects.filter(
            user_id=review.user_id,
            is_published=True,
        ).values_list("rating", "product__brand_id")

        ratings = set()
        brands = set()
        for rating, brand_id in user_reviews:
            ratings.add(rating)
            if brand_id:
                brands.add(brand_id)

        if ratings == {5} and len(brands) <= 1 and len(list(user_reviews)) >= 2:
            return True

    return False


def _is_unverified_5star(review) -> bool:
    """Rule 5: Unverified purchase with a 5-star rating."""
    return not review.is_verified_purchase and review.rating == 5


# ---------------------------------------------------------------------------
# Credibility scoring
# ---------------------------------------------------------------------------

# Penalty weights per flag type (higher = more suspicious)
_FLAG_PENALTIES: dict[str, Decimal] = {
    "copy_paste": Decimal("0.30"),
    "rating_burst": Decimal("0.20"),
    "suspiciously_short": Decimal("0.15"),
    "suspicious_reviewer": Decimal("0.25"),
    "unverified_5star": Decimal("0.10"),
}


def _calculate_credibility(review, fraud_flags: dict[str, bool]) -> Decimal:
    """Compute a credibility score between 0.00 and 1.00.

    Starts at 1.00 (fully credible) and deducts per-flag penalties.
    Bonuses applied for verified purchase and review with media.
    Floor is 0.00.
    """
    score = Decimal("1.00")

    for flag_name, is_set in fraud_flags.items():
        if is_set:
            score -= _FLAG_PENALTIES.get(flag_name, Decimal("0.10"))

    # Bonus: verified purchase adds credibility
    if review.is_verified_purchase:
        score += Decimal("0.10")

    # Bonus: review with media (images/video) is more credible
    if review.media:
        score += Decimal("0.05")

    # Bonus: longer, detailed reviews
    body_len = len(review.body or "")
    if body_len >= 200:
        score += Decimal("0.05")

    return max(Decimal("0.00"), min(Decimal("1.00"), score))
