"""Celery tasks for the rewards app."""
import logging

from celery import shared_task
from django.db.models import F, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue="default")
def award_points_task(
    user_id: str,
    action_type: str,
    reference_id: str | None = None,
    reference_type: str = "",
    description: str = "",
) -> None:
    """Award reward points for a user action (review, referral, etc.).

    Delegates to services.award_points which handles:
    - Idempotency via reference_id
    - Daily / monthly caps
    - Level-up notifications
    """
    from .services import _get_points_for_action, award_points

    points = _get_points_for_action(action_type)
    award_points(
        user_id=user_id,
        points=points,
        action_type=action_type,
        reference_type=reference_type,
        reference_id=reference_id,
        description=description,
    )


@shared_task(queue="default")
def expire_points() -> int:
    """Monthly: expire points past their expiry date.

    For each user with expired ledger entries:
    1. Sum the expired points
    2. Update RewardBalance (current_balance -=, total_expired +=)
    3. Mark those entries so they aren't double-counted

    Returns total points expired across all users.
    """
    from .models import RewardBalance, RewardPointsLedger

    now = timezone.now()
    # Find expired entries that still have positive points (not yet processed)
    expired_qs = RewardPointsLedger.objects.filter(
        expires_at__lte=now,
        points__gt=0,
    )

    if not expired_qs.exists():
        logger.info("expire_points: no points to expire")
        return 0

    # Group by user and sum
    user_totals = expired_qs.values("user_id").annotate(
        total_expired=Sum("points")
    )

    total_expired = 0
    for entry in user_totals:
        user_id = entry["user_id"]
        amount = entry["total_expired"]
        total_expired += amount

        RewardBalance.objects.filter(user_id=user_id).update(
            current_balance=F("current_balance") - amount,
            total_expired=F("total_expired") + amount,
        )

    # Push expires_at far out so these entries aren't processed again.
    # We preserve the original points value for audit trail.
    count = expired_qs.update(
        expires_at=now + timezone.timedelta(days=36500),
    )

    logger.info(
        "expire_points: expired %d points across %d ledger entries",
        total_expired,
        count,
    )
    return total_expired


@shared_task(queue="default")
def fulfill_gift_card(redemption_id: str) -> None:
    """Fulfill a gift card redemption (placeholder for external API integration).

    In production, this would call the fulfillment partner's API.
    For now, it logs the attempt for manual fulfillment by admin.
    """
    from .models import GiftCardRedemption

    redemption = GiftCardRedemption.objects.filter(pk=redemption_id).first()
    if not redemption:
        logger.warning("fulfill_gift_card: redemption %s not found", redemption_id)
        return

    if redemption.status != GiftCardRedemption.Status.PENDING:
        logger.info(
            "fulfill_gift_card: redemption %s already %s",
            redemption_id,
            redemption.status,
        )
        return

    # TODO: Integrate with fulfillment partner API (e.g., Xoxoday, QwikCilver)
    logger.info(
        "fulfill_gift_card: redemption %s for %s ₹%s queued for manual fulfillment",
        redemption_id,
        redemption.catalog.brand_name,
        redemption.denomination,
    )


@shared_task(queue="default")
def clawback_review_points_task(user_id: str, review_id: str) -> None:
    """Clawback points when a review is removed by a moderator."""
    from .services import clawback_review_points

    clawback_review_points(user_id=user_id, review_id=review_id)
