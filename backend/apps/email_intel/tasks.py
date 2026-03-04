"""Email intelligence Celery tasks.

All tasks run on the 'email' queue.
"""

import structlog
from celery import shared_task

logger = structlog.get_logger(__name__)


@shared_task(
    queue="email",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
)
def process_inbound_email(self, email_id: str) -> None:
    """Parse inbound email: categorize, extract order/refund data.

    Retry up to 3 times with exponential backoff (60s, 120s, 240s).
    If all retries fail: set parse_status='failed_permanent'.
    """
    from .models import InboxEmail
    from .parsers import parse_email

    try:
        parse_email(email_id)
    except Exception as exc:
        # Check if we've exhausted all retries
        if self.request.retries >= self.max_retries:
            logger.error(
                "email_parse_failed_permanent",
                email_id=email_id,
                retries=self.request.retries,
            )
            try:
                InboxEmail.objects.filter(id=email_id).update(
                    parse_status=InboxEmail.ParseStatus.FAILED_PERMANENT
                )
            except Exception:
                logger.exception(
                    "failed_to_update_parse_status", email_id=email_id
                )
            return

        logger.warning(
            "email_parse_retry",
            email_id=email_id,
            retry=self.request.retries + 1,
            max_retries=self.max_retries,
            exc=str(exc),
        )
        raise


@shared_task(queue="email")
def send_return_window_alert(return_window_id: str, days_remaining: int) -> None:
    """Send alert for a return window expiring in N days."""
    from apps.accounts.models import Notification
    from .models import ReturnWindow

    try:
        rw = ReturnWindow.objects.select_related("order", "user").get(
            id=return_window_id
        )
    except ReturnWindow.DoesNotExist:
        logger.warning(
            "return_window_not_found", return_window_id=return_window_id
        )
        return

    # Check if alert already sent
    if days_remaining == 3 and rw.alert_sent_3day:
        return
    if days_remaining == 1 and rw.alert_sent_1day:
        return

    product_name = rw.order.product_name if rw.order else "your order"

    Notification.objects.create(
        user=rw.user,
        type=Notification.Type.RETURN_WINDOW,
        title=f"Return window expires in {days_remaining} day{'s' if days_remaining > 1 else ''}",
        body=f"The return window for \"{product_name[:100]}\" expires on {rw.window_end_date}.",
        action_url="/purchases/return-windows",
        action_label="View Return Windows",
        entity_type="return_window",
        entity_id=str(rw.id),
    )

    # Mark alert as sent
    if days_remaining == 3:
        rw.alert_sent_3day = True
        rw.save(update_fields=["alert_sent_3day"])
    elif days_remaining == 1:
        rw.alert_sent_1day = True
        rw.save(update_fields=["alert_sent_1day"])

    logger.info(
        "return_window_alert_sent",
        return_window_id=return_window_id,
        days_remaining=days_remaining,
    )


@shared_task(queue="email")
def check_return_window_alerts() -> None:
    """Daily: send alerts for return windows expiring in 3 or 1 day."""
    from datetime import timedelta

    from django.utils import timezone

    from .models import ReturnWindow

    today = timezone.now().date()

    # 3-day alerts
    windows_3day = ReturnWindow.objects.filter(
        window_end_date=today + timedelta(days=3),
        alert_sent_3day=False,
    )
    for rw in windows_3day:
        send_return_window_alert.delay(str(rw.id), 3)

    # 1-day alerts
    windows_1day = ReturnWindow.objects.filter(
        window_end_date=today + timedelta(days=1),
        alert_sent_1day=False,
    )
    for rw in windows_1day:
        send_return_window_alert.delay(str(rw.id), 1)


@shared_task(queue="email")
def detect_refund_delays() -> None:
    """Daily: check pending refunds that exceeded expected timeline."""
    from django.utils import timezone
    from apps.accounts.models import Notification
    from .models import RefundTracking

    now = timezone.now()

    # Find refunds past their expected_by date that haven't been completed
    delayed_refunds = RefundTracking.objects.filter(
        status__in=["initiated", "processing"],
        expected_by__lt=now,
        delay_days__isnull=True,
    ).select_related("user", "order")

    for refund in delayed_refunds:
        delay = (now - refund.expected_by).days if refund.expected_by else 0
        refund.delay_days = delay
        refund.save(update_fields=["delay_days", "updated_at"])

        product_name = refund.order.product_name if refund.order else "your order"

        Notification.objects.create(
            user=refund.user,
            type=Notification.Type.REFUND_DELAY,
            title=f"Refund delayed by {delay} day{'s' if delay != 1 else ''}",
            body=f"Your refund for \"{product_name[:100]}\" from {refund.marketplace} is overdue.",
            action_url="/purchases/refunds",
            action_label="View Refunds",
            entity_type="refund_tracking",
            entity_id=str(refund.id),
        )

    if delayed_refunds:
        logger.info(
            "refund_delays_detected",
            count=len(delayed_refunds),
        )
