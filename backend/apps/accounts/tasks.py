"""Celery tasks for accounts app."""
from celery import shared_task


@shared_task(queue="default")
def send_verification_email(user_id: str) -> None:
    """Send email verification link to new user."""
    # TODO Sprint 1 Week 2
    pass


@shared_task(queue="default")
def delete_user_data(user_id: str) -> None:
    """Hard-delete all user data (DPDP compliance). Called 30 days after soft-delete."""
    # TODO Sprint 4
    pass


@shared_task(queue="email")
def sync_gmail_account(user_id: str) -> None:
    """Background Gmail OAuth sync — runs every 6 hours per connected user."""
    # TODO Sprint 2 (P1 feature)
    pass
