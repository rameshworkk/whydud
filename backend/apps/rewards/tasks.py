from celery import shared_task

@shared_task(queue="default")
def award_points(user_id: str, action_type: str, reference_id: str | None = None) -> None:
    """Award reward points for a user action (review, referral, etc.)."""
    # TODO Sprint 4 Week 11
    pass

@shared_task(queue="default")
def expire_points() -> None:
    """Monthly: expire points past their expiry date."""
    # TODO Sprint 4 Week 11
    pass
