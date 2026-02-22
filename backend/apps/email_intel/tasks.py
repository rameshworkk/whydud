from celery import shared_task

@shared_task(queue="email")
def process_inbound_email(email_id: str) -> None:
    """Parse inbound email: categorize, extract order/refund data."""
    # TODO Sprint 3 Week 8
    pass

@shared_task(queue="email")
def check_return_window_alerts() -> None:
    """Daily: send alerts for return windows expiring in 3 or 1 day."""
    # TODO Sprint 4 Week 11
    pass

@shared_task(queue="email")
def detect_refund_delays() -> None:
    """Daily: check pending refunds that exceeded expected timeline."""
    # TODO Sprint 4 Week 11
    pass
