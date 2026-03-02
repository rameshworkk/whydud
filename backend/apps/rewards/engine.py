"""Rewards engine — point award logic."""
from datetime import timedelta

from django.db.models import F
from django.utils.timezone import now

from .models import RewardBalance, RewardPointsLedger

ACTION_POINTS = {
    'write_review': 20,
    'review_with_photo': 30,       # bonus for photos
    'review_with_video': 50,       # bonus for video
    'connect_email': 50,
    'referral_signup': 30,
    'first_purchase_tracked': 25,
    'verified_purchase_review': 40,
}


def award_points(user_id, action_type, reference_id=None):
    """Award points for an action. Idempotent per reference_id."""

    if reference_id:
        exists = RewardPointsLedger.objects.filter(
            user_id=user_id, action_type=action_type, reference_id=reference_id
        ).exists()
        if exists:
            return  # Already awarded

    points = ACTION_POINTS.get(action_type, 0)
    if points == 0:
        return

    RewardPointsLedger.objects.create(
        user_id=user_id, points=points, action_type=action_type,
        reference_id=reference_id, expires_at=now() + timedelta(days=365)
    )

    updated = RewardBalance.objects.filter(user_id=user_id).update(
        total_earned=F('total_earned') + points,
        current_balance=F('current_balance') + points
    )
    # Create balance row if it doesn't exist yet
    if updated == 0:
        RewardBalance.objects.create(
            user_id=user_id,
            total_earned=points,
            current_balance=points,
        )
