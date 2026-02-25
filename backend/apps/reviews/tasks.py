"""Celery tasks for reviews app."""
import logging

from celery import shared_task
from django.db import models
from django.utils import timezone

logger = logging.getLogger(__name__)

# Level thresholds (inclusive lower bound → level)
LEVEL_THRESHOLDS: list[tuple[int, str]] = [
    (30, "platinum"),
    (15, "gold"),
    (5, "silver"),
    (1, "bronze"),
]


def _level_for_count(total_reviews: int) -> str:
    """Return reviewer level based on total published review count."""
    for threshold, level in LEVEL_THRESHOLDS:
        if total_reviews >= threshold:
            return level
    return "bronze"


@shared_task(queue="scoring")
def run_sentiment_analysis(review_id: str) -> None:
    """Run spaCy + TextBlob sentiment analysis on a review."""
    # TODO Sprint 3 Week 7
    pass


@shared_task(queue="scoring")
def detect_fake_reviews(product_id: str) -> dict:
    """Rule-based fake review detection (copy-paste, burst, distribution).

    Runs 5 heuristic checks per review:
      1. Copy-paste / duplicate content (content_hash)
      2. Rating burst (many same-rating reviews in one day)
      3. Suspiciously short 5-star reviews
      4. Reviewer account patterns (new account, only 5-star, single brand)
      5. Unverified purchase with 5-star rating

    Updates ``fraud_flags``, ``credibility_score``, and ``is_flagged`` on
    each review. Returns summary dict: ``{total, flagged, updated}``.
    """
    from .fraud_detection import detect_fake_reviews as _run_detection

    result = _run_detection(product_id)
    logger.info(
        "detect_fake_reviews task product=%s result=%s",
        product_id,
        result,
    )
    return result


@shared_task(queue="scoring")
def aggregate_review_sentiment(product_id: str) -> None:
    """Generate AI summary: top 3 pros, top 3 cons for a product."""
    # TODO Sprint 3 Week 7
    pass


@shared_task(queue="default")
def publish_pending_reviews() -> int:
    """Publish reviews past their 48-hour hold period.

    Runs every hour via Celery Beat. Reviews submitted by Whydud users are
    held for 48h (``publish_at`` set at creation). This task bulk-publishes
    all reviews whose hold has expired.

    Returns the number of reviews published.
    """
    from .models import Review

    now = timezone.now()
    count = (
        Review.objects.filter(is_published=False, publish_at__lte=now)
        .update(is_published=True, updated_at=now)
    )

    if count:
        logger.info("publish_pending_reviews: published %d reviews", count)

    return count


@shared_task(queue="scoring")
def update_reviewer_profiles() -> int:
    """Recalculate reviewer stats, levels, and leaderboard ranks.

    Runs every Monday 00:00 UTC via Celery Beat.

    For each user who has written at least one published Whydud review:
      1. Count total published reviews
      2. Sum upvotes and helpful_votes received across all reviews
      3. Average credibility_score (where available) as review_quality_avg
      4. Assign level: bronze (1-4), silver (5-14), gold (15-29), platinum (30+)
      5. Rank all profiles by total_upvotes_received → leaderboard_rank
      6. Top 10 → is_top_reviewer = True

    Returns the number of profiles updated.
    """
    from .models import Review, ReviewerProfile

    # --- Aggregate stats per user ------------------------------------------
    user_stats = (
        Review.objects.filter(
            user__isnull=False,
            is_published=True,
            source=Review.Source.WHYDUD,
        )
        .values("user_id")
        .annotate(
            total_reviews=models.Count("id"),
            total_upvotes=models.Sum("upvotes"),
            total_helpful=models.Sum("helpful_votes"),
            avg_quality=models.Avg(
                "credibility_score",
                filter=models.Q(credibility_score__isnull=False),
            ),
        )
    )

    if not user_stats:
        logger.info("update_reviewer_profiles: no reviewers found")
        return 0

    # --- Upsert profiles and assign levels ---------------------------------
    profiles_by_user: dict[str, ReviewerProfile] = {}

    for stats in user_stats:
        user_id = stats["user_id"]
        total_reviews = stats["total_reviews"] or 0
        total_upvotes = stats["total_upvotes"] or 0
        total_helpful = stats["total_helpful"] or 0
        avg_quality = stats["avg_quality"] or 0

        profile, _created = ReviewerProfile.objects.get_or_create(
            user_id=user_id,
        )
        profile.total_reviews = total_reviews
        profile.total_upvotes_received = total_upvotes
        profile.total_helpful_votes = total_helpful
        profile.review_quality_avg = round(avg_quality, 2)
        profile.reviewer_level = _level_for_count(total_reviews)
        profiles_by_user[str(user_id)] = profile

    # --- Rank by total_upvotes_received (descending) -----------------------
    ranked = sorted(
        profiles_by_user.values(),
        key=lambda p: p.total_upvotes_received,
        reverse=True,
    )

    for rank, profile in enumerate(ranked, start=1):
        profile.leaderboard_rank = rank
        profile.is_top_reviewer = rank <= 10

    # --- Bulk save ---------------------------------------------------------
    fields_to_update = [
        "total_reviews",
        "total_upvotes_received",
        "total_helpful_votes",
        "review_quality_avg",
        "reviewer_level",
        "leaderboard_rank",
        "is_top_reviewer",
        "updated_at",
    ]
    now = timezone.now()
    for profile in ranked:
        profile.updated_at = now

    ReviewerProfile.objects.bulk_update(ranked, fields_to_update, batch_size=500)

    logger.info(
        "update_reviewer_profiles: updated %d profiles (top reviewer: %s)",
        len(ranked),
        ranked[0].user_id if ranked else "none",
    )

    return len(ranked)
