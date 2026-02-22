from celery import shared_task

@shared_task(queue="scoring")
def detect_blockbuster_deals() -> None:
    """Every 30 minutes: scan for error pricing and lowest-ever prices."""
    # TODO Sprint 4 Week 10
    pass
