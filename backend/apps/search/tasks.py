"""Celery tasks for Meilisearch index synchronisation.

Tasks run on the ``scoring`` queue (shared with DudScore computation).
Document format matches ``ProductListSerializer`` fields so search views
and autocomplete work without transformation.
"""
import logging

from celery import shared_task

logger = logging.getLogger(__name__)

# Batch size for Meilisearch add_documents calls
_BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_client():
    """Return a configured Meilisearch client, or raise ImportError/ValueError."""
    import meilisearch
    from django.conf import settings

    url = getattr(settings, "MEILISEARCH_URL", None)
    key = getattr(settings, "MEILISEARCH_MASTER_KEY", "")
    if not url:
        raise ValueError("MEILISEARCH_URL not configured in Django settings")
    return meilisearch.Client(url, key)


def _product_to_document(product) -> dict:
    """Convert a Product instance to a Meilisearch document.

    Includes all searchable, filterable, sortable, and display fields
    expected by SearchView and AutocompleteView.
    """
    return {
        "id": str(product.id),
        "slug": product.slug,
        "title": product.title,
        "description": product.description or "",
        "brand_name": product.brand.name if product.brand else "",
        "brand_slug": product.brand.slug if product.brand else "",
        "category_name": product.category.name if product.category else "",
        "category_slug": product.category.slug if product.category else "",
        "current_best_price": float(product.current_best_price) if product.current_best_price else 0,
        "current_best_marketplace": product.current_best_marketplace or "",
        "lowest_price_ever": float(product.lowest_price_ever) if product.lowest_price_ever else None,
        "avg_rating": float(product.avg_rating) if product.avg_rating else 0,
        "total_reviews": product.total_reviews,
        "dud_score": float(product.dud_score) if product.dud_score else 0,
        "dud_score_confidence": product.dud_score_confidence or "",
        "images": product.images or [],
        "image_url": product.images[0] if product.images else "",
        "is_refurbished": product.is_refurbished,
        "status": product.status,
        "in_stock": product.current_best_price is not None,
        "created_at": product.created_at.timestamp() if product.created_at else 0,
    }


def _configure_index(index) -> None:
    """Set searchable, filterable, and sortable attributes on the index.

    Matches the configuration in ``sync_meilisearch`` management command.
    """
    index.update_settings({
        "searchableAttributes": [
            "title",
            "brand_name",
            "category_name",
            "description",
        ],
        "filterableAttributes": [
            "category_slug",
            "brand_slug",
            "current_best_price",
            "dud_score",
            "status",
            "in_stock",
        ],
        "sortableAttributes": [
            "current_best_price",
            "dud_score",
            "avg_rating",
            "total_reviews",
            "created_at",
        ],
        "displayedAttributes": ["*"],
    })


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@shared_task(queue="scoring")
def sync_products_to_meilisearch(product_ids: list[str] | None = None) -> dict:
    """Sync products to Meilisearch index.

    Args:
        product_ids: If given, sync only these product UUIDs.
                     If None, sync all active products (full sync).

    Returns:
        Summary dict with synced count and any errors.
    """
    from apps.products.models import Product

    try:
        client = _get_client()
    except (ImportError, ValueError) as exc:
        logger.warning("Meilisearch unavailable, skipping sync: %s", exc)
        return {"success": False, "error": str(exc)}

    index = client.index("products")

    if product_ids:
        products = (
            Product.objects
            .select_related("brand", "category")
            .filter(id__in=product_ids)
        )
    else:
        products = (
            Product.objects
            .select_related("brand", "category")
            .filter(status=Product.Status.ACTIVE)
        )

    total = products.count()
    synced = 0
    errors = 0

    for offset in range(0, total, _BATCH_SIZE):
        batch = products[offset:offset + _BATCH_SIZE]
        documents = [_product_to_document(p) for p in batch]

        try:
            task_info = index.add_documents(documents, primary_key="id")
            client.wait_for_task(task_info.task_uid, timeout_in_ms=60_000)
            synced += len(documents)
        except Exception:
            logger.exception(
                "Meilisearch batch sync failed (offset=%d, count=%d)",
                offset, len(documents),
            )
            errors += len(documents)

    logger.info(
        "Meilisearch sync complete: %d synced, %d errors (of %d total)",
        synced, errors, total,
    )

    return {"success": errors == 0, "synced": synced, "errors": errors, "total": total}


@shared_task(queue="scoring")
def full_reindex() -> dict:
    """Full reindex: configure index settings, then sync all active products.

    Registered in Celery Beat for daily execution at 03:00 UTC.
    """
    try:
        client = _get_client()
    except (ImportError, ValueError) as exc:
        logger.warning("Meilisearch unavailable, skipping full reindex: %s", exc)
        return {"success": False, "error": str(exc)}

    index = client.index("products")

    logger.info("Configuring Meilisearch index settings...")
    _configure_index(index)

    logger.info("Starting full product reindex...")
    return sync_products_to_meilisearch()
