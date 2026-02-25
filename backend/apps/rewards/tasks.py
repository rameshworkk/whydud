from celery import shared_task


@shared_task(queue="default")
def award_points_task(user_id: str, action_type: str, reference_id: str | None = None) -> None:
    """Award reward points for a user action (review, referral, etc.)."""
    from .engine import award_points
    award_points(user_id, action_type, reference_id)


@shared_task(queue="default")
def expire_points() -> None:
    """Monthly: expire points past their expiry date."""
    # TODO Sprint 4 Week 11
    pass
