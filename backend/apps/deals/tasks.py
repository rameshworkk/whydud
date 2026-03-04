import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    queue="scoring",
    soft_time_limit=600,   # 10 min soft limit
    time_limit=720,        # 12 min hard limit
)
def detect_blockbuster_deals() -> dict:
    """Periodic task: scan for error pricing, lowest-ever, flash sales, and genuine discounts."""
    from apps.deals.detection import detect_deals

    return detect_deals()
