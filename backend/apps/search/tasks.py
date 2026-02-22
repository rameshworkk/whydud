from celery import shared_task

@shared_task(queue="scoring")
def index_product(product_id: str) -> None:
    """Index or update a product in Meilisearch."""
    # TODO Sprint 1 Week 3
    pass

@shared_task(queue="scoring")
def full_reindex() -> None:
    """Full reindex of all active products to Meilisearch."""
    # TODO Sprint 1 Week 3
    pass
