"""Rewards service layer — award, deduct, clawback, and balance logic.

All point values are read from ``common.app_settings.RewardsConfig`` so they
can be tuned at runtime without code changes.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import F, Sum
from django.utils import timezone

from common.app_settings import RewardsConfig

from .models import RewardBalance, RewardPointsLedger

logger = logging.getLogger(__name__)

# Maps action_type → RewardsConfig accessor name.
# Keeps the single source of truth in app_settings.py.
ACTION_POINTS_MAP: dict[str, str] = {
    "write_review": "points_write_review",
    "review_with_photo": "points_review_with_photo",
    "review_with_video": "points_review_with_video",
    "connect_email": "points_connect_email",
    "referral_signup": "points_referral_signup",
    "first_purchase_tracked": "points_first_purchase_tracked",
    "verified_purchase_review": "points_verified_purchase_review",
    "daily_login_streak": "points_daily_login_streak",
    "review_popular": "points_review_popular",
}

# Level thresholds ordered highest-first for quick matching.
LEVEL_LABELS = {
    "bronze": "Bronze",
    "silver": "Silver",
    "gold": "Gold",
    "platinum": "Platinum",
}


def _get_points_for_action(action_type: str) -> int:
    """Look up point value for an action via RewardsConfig."""
    accessor = ACTION_POINTS_MAP.get(action_type)
    if not accessor:
        return 0
    return getattr(RewardsConfig, accessor)()


def _level_for_points(total_earned: int) -> str:
    """Return reviewer level based on total earned points."""
    thresholds = RewardsConfig.level_thresholds()
    # Sort descending so we match highest first
    for level in ("platinum", "gold", "silver", "bronze"):
        if total_earned >= thresholds.get(level, 0):
            return level
    return "bronze"


def _earned_today(user_id) -> int:
    """Sum of positive points earned by user today (UTC)."""
    today = timezone.now().date()
    result = (
        RewardPointsLedger.objects.filter(
            user_id=user_id,
            points__gt=0,
            created_at__date=today,
        )
        .aggregate(total=Sum("points"))
    )
    return result["total"] or 0


def _earned_this_month(user_id) -> int:
    """Sum of positive points earned by user this calendar month."""
    now = timezone.now()
    result = (
        RewardPointsLedger.objects.filter(
            user_id=user_id,
            points__gt=0,
            created_at__year=now.year,
            created_at__month=now.month,
        )
        .aggregate(total=Sum("points"))
    )
    return result["total"] or 0


@transaction.atomic
def award_points(
    user_id,
    points: int,
    action_type: str,
    reference_type: str = "",
    reference_id=None,
    description: str = "",
) -> RewardPointsLedger | None:
    """Award points for a user action.

    1. Idempotent per (user, action_type, reference_id).
    2. Checks daily cap (100 pts/day) and monthly cap (500 pts/month).
    3. Creates ledger row with 365-day expiry.
    4. Updates RewardBalance atomically.
    5. If level threshold crossed → creates Notification.

    Returns the ledger entry, or None if skipped (duplicate / cap hit).
    """
    # Resolve points from config if not explicitly provided
    if points <= 0:
        points = _get_points_for_action(action_type)
    if points <= 0:
        return None

    # Idempotency: skip if already awarded for this reference
    if reference_id:
        exists = RewardPointsLedger.objects.filter(
            user_id=user_id,
            action_type=action_type,
            reference_id=reference_id,
        ).exists()
        if exists:
            logger.debug(
                "award_points skip duplicate user=%s action=%s ref=%s",
                user_id, action_type, reference_id,
            )
            return None

    # Daily cap check
    daily_cap = RewardsConfig.daily_cap()
    earned_today = _earned_today(user_id)
    if earned_today >= daily_cap:
        logger.info(
            "award_points daily cap user=%s earned=%d cap=%d",
            user_id, earned_today, daily_cap,
        )
        return None
    # Clamp to remaining daily allowance
    points = min(points, daily_cap - earned_today)

    # Monthly cap check
    monthly_cap = RewardsConfig.monthly_cap()
    earned_month = _earned_this_month(user_id)
    if earned_month >= monthly_cap:
        logger.info(
            "award_points monthly cap user=%s earned=%d cap=%d",
            user_id, earned_month, monthly_cap,
        )
        return None
    points = min(points, monthly_cap - earned_month)

    if points <= 0:
        return None

    # Auto-generate description if not provided
    if not description:
        description = f"Earned {points} points for {action_type.replace('_', ' ')}"

    expiry_days = RewardsConfig.expiry_days()
    entry = RewardPointsLedger.objects.create(
        user_id=user_id,
        points=points,
        action_type=action_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
        expires_at=timezone.now() + timedelta(days=expiry_days),
    )

    # Upsert balance
    updated = RewardBalance.objects.filter(user_id=user_id).update(
        total_earned=F("total_earned") + points,
        current_balance=F("current_balance") + points,
    )
    if updated == 0:
        RewardBalance.objects.create(
            user_id=user_id,
            total_earned=points,
            current_balance=points,
        )

    logger.info(
        "award_points user=%s action=%s points=%d ref=%s",
        user_id, action_type, points, reference_id,
    )

    # Check level threshold and notify if crossed
    _check_level_up(user_id)

    return entry


@transaction.atomic
def deduct_points(
    user_id,
    points: int,
    action_type: str = "clawback",
    reference_type: str = "",
    reference_id=None,
    description: str = "",
) -> RewardPointsLedger | None:
    """Deduct points from a user's balance (clawback or redemption).

    Returns the ledger entry, or None if the user has no balance to deduct from.
    """
    if points <= 0:
        return None

    balance = RewardBalance.objects.filter(user_id=user_id).first()
    if not balance or balance.current_balance <= 0:
        return None

    # Don't deduct more than they have
    actual_deduction = min(points, balance.current_balance)

    if not description:
        description = f"Deducted {actual_deduction} points ({action_type.replace('_', ' ')})"

    entry = RewardPointsLedger.objects.create(
        user_id=user_id,
        points=-actual_deduction,
        action_type=action_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )

    RewardBalance.objects.filter(user_id=user_id).update(
        total_spent=F("total_spent") + actual_deduction,
        current_balance=F("current_balance") - actual_deduction,
    )

    logger.info(
        "deduct_points user=%s action=%s points=%d ref=%s",
        user_id, action_type, actual_deduction, reference_id,
    )

    return entry


def get_balance(user_id) -> RewardBalance:
    """Get or create a user's reward balance."""
    balance, _ = RewardBalance.objects.get_or_create(user_id=user_id)
    return balance


def clawback_review_points(user_id, review_id) -> RewardPointsLedger | None:
    """Clawback points awarded for a review that was removed by a moderator.

    Finds the original award and reverses it.
    """
    original = RewardPointsLedger.objects.filter(
        user_id=user_id,
        action_type="write_review",
        reference_id=review_id,
        points__gt=0,
    ).first()

    if not original:
        return None

    return deduct_points(
        user_id=user_id,
        points=original.points,
        action_type="clawback",
        reference_type="review",
        reference_id=review_id,
        description=f"Points clawed back: review {review_id} removed by moderator",
    )


def _check_level_up(user_id) -> None:
    """Check if user crossed a level threshold and create notification."""
    balance = RewardBalance.objects.filter(user_id=user_id).first()
    if not balance:
        return

    new_level = _level_for_points(balance.total_earned)

    # Check the previous level before this award by looking at total minus latest entry
    last_entry = (
        RewardPointsLedger.objects.filter(user_id=user_id, points__gt=0)
        .order_by("-created_at")
        .first()
    )
    if not last_entry:
        return

    old_total = balance.total_earned - last_entry.points
    old_level = _level_for_points(old_total)

    if new_level != old_level and new_level != "bronze":
        _create_level_notification(user_id, new_level)
        # Also update ReviewerProfile level
        _update_reviewer_level(user_id, new_level)


def _create_level_notification(user_id, level: str) -> None:
    """Create an in-app notification for reaching a new reviewer level."""
    try:
        from apps.accounts.models import Notification

        label = LEVEL_LABELS.get(level, level.title())
        Notification.objects.create(
            user_id=user_id,
            type=Notification.Type.LEVEL_UP,
            title=f"You reached {label} reviewer!",
            body=f"Congratulations! You've earned enough points to reach {label} level. Keep reviewing to unlock more rewards.",
            action_url="/rewards",
            action_label="View Rewards",
        )
    except Exception:
        logger.exception("Failed to create level-up notification for user=%s", user_id)


def _update_reviewer_level(user_id, level: str) -> None:
    """Sync the reviewer level on ReviewerProfile when points threshold is crossed."""
    try:
        from apps.reviews.models import ReviewerProfile

        ReviewerProfile.objects.filter(user_id=user_id).update(
            reviewer_level=level,
        )
    except Exception:
        logger.exception("Failed to update reviewer level for user=%s", user_id)
