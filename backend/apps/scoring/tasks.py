from celery import shared_task

@shared_task(queue="scoring")
def compute_dudscore(product_id: str) -> None:
    """Compute DudScore v1 for a product using current active config."""
    # TODO Sprint 3 Week 7
    pass

@shared_task(queue="scoring")
def full_dudscore_recalculation() -> None:
    """Monthly: recalculate DudScore for all products."""
    # TODO Sprint 3 Week 7
    pass
