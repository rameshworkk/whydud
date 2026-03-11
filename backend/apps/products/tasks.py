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
    from apps.products.matching import update_canonical_product
    from apps.products.models import Product

    try:
        product = Product.objects.get(id=product_id)
        update_canonical_product(product)
    except Product.DoesNotExist:
        pass


@shared_task(queue="default")
def repair_stale_best_prices() -> dict:
    """Fix products where current_best_price is NULL but in-stock listings exist.

    One-time repair for the enrichment bug where enrich_via_http updated
    listing prices without recalculating Product.current_best_price.
    """
    import logging

    from apps.products.matching import update_canonical_product
    from apps.products.models import Product, ProductListing

    logger = logging.getLogger(__name__)

    # Products with NULL best price but in-stock listings with a price
    broken_ids = list(
        ProductListing.objects.filter(
            in_stock=True,
            current_price__isnull=False,
            product__current_best_price__isnull=True,
        )
        .values_list("product_id", flat=True)
        .distinct()
    )

    fixed = 0
    for pid in broken_ids:
        try:
            product = Product.objects.get(id=pid)
            update_canonical_product(product)
            fixed += 1
        except Exception:
            logger.exception("Failed to repair product %s", pid)

    logger.info("repair_stale_best_prices: fixed %d / %d products", fixed, len(broken_ids))
    return {"found": len(broken_ids), "fixed": fixed}
