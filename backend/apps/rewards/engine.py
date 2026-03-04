"""Rewards engine — backward-compatible wrapper around services.py.

Existing callers (tasks.py, reviews/services.py) import from here.
All logic now lives in services.py.
"""
from common.app_settings import RewardsConfig

from .services import award_points as _award_points

# Legacy dict kept for reference — actual values come from RewardsConfig.
ACTION_POINTS = {
    "write_review": RewardsConfig.points_write_review,
    "review_with_photo": RewardsConfig.points_review_with_photo,
    "review_with_video": RewardsConfig.points_review_with_video,
    "connect_email": RewardsConfig.points_connect_email,
    "referral_signup": RewardsConfig.points_referral_signup,
    "first_purchase_tracked": RewardsConfig.points_first_purchase_tracked,
    "verified_purchase_review": RewardsConfig.points_verified_purchase_review,
    "daily_login_streak": RewardsConfig.points_daily_login_streak,
    "review_popular": RewardsConfig.points_review_popular,
}


def award_points(user_id, action_type: str, reference_id=None):
    """Award points for an action. Delegates to services.award_points."""
    from .services import _get_points_for_action

    points = _get_points_for_action(action_type)
    _award_points(
        user_id=user_id,
        points=points,
        action_type=action_type,
        reference_id=reference_id,
    )
