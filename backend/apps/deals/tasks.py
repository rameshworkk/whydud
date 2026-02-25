import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(queue="scoring")
def detect_blockbuster_deals() -> dict:
    """Periodic task: scan for error pricing, lowest-ever, and genuine discounts."""
    from apps.deals.detection import detect_deals

    return detect_deals()
