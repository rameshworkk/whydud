from celery import shared_task

@shared_task(queue="email", bind=True, max_retries=3, default_retry_delay=60)
def process_inbound_email(self, email_id: str) -> None:
    """Parse inbound email: categorize, extract order/refund data."""
    from .parsers import parse_email

    try:
        parse_email(email_id)
    except Exception as exc:
        self.retry(exc=exc)

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
