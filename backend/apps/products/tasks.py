"""Celery tasks for products app."""
from celery import shared_task


@shared_task(queue="scoring")
def reindex_product_in_meilisearch(product_id: str) -> None:
    """Push product update to Meilisearch index."""
    # TODO Sprint 1 Week 3
    pass


@shared_task(queue="default")
def update_product_aggregate_stats(product_id: str) -> None:
    """Recalculate avg_rating, total_reviews, current_best_price."""
    # TODO Sprint 2 Week 5
    pass
