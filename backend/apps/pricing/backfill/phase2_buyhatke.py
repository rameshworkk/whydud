"""Phase 2: Bulk price history fill from BuyHatke.

For every discovered product (from Phase 1) with an ASIN/FSID,
call BuyHatke's open API to get ~17 months of price history.

For products that match an existing ProductListing, price points
are injected directly into ``price_snapshots``. Products without
a matching listing still get their metadata updated (point count,
predictions) so Phase 4 can re-run injection after spider enrichment.

Speed: ~120 products/minute with default settings (0.5s delay, 5 concurrent).

Usage::

    python manage.py backfill_prices bh-fill --batch 5000
    python manage.py backfill_prices bh-fill --marketplace amazon-in
"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async

from apps.pricing.backfill.bh_client import BHClient
from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


def _query_batch_and_listings(
    batch_size: int, marketplace_slug: str | None
) -> tuple[list, dict]:
    """Synchronous ORM queries for batch + listing map."""
    from apps.products.models import ProductListing

    supported_slugs = list(BackfillConfig.bh_pos_map().keys())

    qs = BackfillProduct.objects.filter(
        status=BackfillProduct.Status.DISCOVERED,
    ).exclude(
        external_id="",
    ).filter(
        marketplace_slug__in=supported_slugs,
    )

    if marketplace_slug:
        qs = qs.filter(marketplace_slug=marketplace_slug)

    batch = list(qs.order_by("created_at")[:batch_size])

    # Pre-fetch existing listings for batch matching
    listing_map: dict[tuple[str, str], dict] = {}
    if batch:
        external_pairs = [(bp.marketplace_slug, bp.external_id) for bp in batch]
        for listing in ProductListing.objects.filter(
            marketplace__slug__in={ms for ms, _ in external_pairs},
            external_id__in={eid for _, eid in external_pairs},
        ).select_related("marketplace"):
            key = (listing.marketplace.slug, listing.external_id)
            listing_map[key] = {
                "listing_id": str(listing.id),
                "product_id": str(listing.product_id),
                "marketplace_id": listing.marketplace_id,
            }

    return batch, listing_map


def _save_bp_filled(bp, result, listing_info):
    """Synchronous save for a successfully filled BackfillProduct."""
    bp.price_data_points = result.point_count
    if result.price_points:
        bp.history_from = result.price_points[0].time
        bp.history_to = result.price_points[-1].time

    pred = result.prediction
    bp.bh_prediction_days = pred.get("days")
    bp.bh_prediction_weeks = pred.get("weeks")
    bp.bh_prediction_months = pred.get("months")

    bp.status = BackfillProduct.Status.BH_FILLED
    bp.error_message = ""

    injected_count = 0
    if listing_info:
        injected_count = inject_price_points(
            listing_id=listing_info["listing_id"],
            product_id=listing_info["product_id"],
            marketplace_id=listing_info["marketplace_id"],
            price_points=result.price_points,
            source="buyhatke",
        )
        bp.product_listing_id = listing_info["listing_id"]

    bp.save()
    return injected_count


def _save_bp_empty(bp):
    """Synchronous save for empty result."""
    bp.status = BackfillProduct.Status.BH_FILLED
    bp.save(update_fields=["status", "updated_at"])


def _save_bp_failed(bp, error_msg):
    """Synchronous save for failed result."""
    bp.status = BackfillProduct.Status.FAILED
    bp.error_message = error_msg[:500]
    bp.retry_count += 1
    bp.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


async def buyhatke_bulk_fill(
    batch_size: int | None = None,
    marketplace_slug: str | None = None,
    delay: float | None = None,
) -> dict:
    """Phase 2: For all discovered products, fetch BuyHatke price history.

    Args:
        batch_size: Max products to process in this run.
        marketplace_slug: Filter by marketplace slug.
        delay: Override BH request delay.

    Returns:
        Stats dict with counts.
    """
    batch_size = batch_size or BackfillConfig.phase2_batch_size()

    batch, listing_map = await sync_to_async(_query_batch_and_listings)(
        batch_size, marketplace_slug
    )
    total = len(batch)

    if total == 0:
        logger.info("Phase 2: no discovered products to fill")
        return {"total": 0, "filled": 0, "injected": 0, "empty": 0, "failed": 0, "points": 0}

    logger.info("Phase 2: BuyHatke bulk fill for %d products", total)
    stats = {"total": total, "filled": 0, "injected": 0, "empty": 0, "failed": 0, "points": 0}

    async with BHClient(delay=delay) as client:
        for i, bp in enumerate(batch):
            try:
                result = await client.fetch_price_history(
                    pid=bp.external_id,
                    marketplace_slug=bp.marketplace_slug,
                )

                if not result.found or result.point_count == 0:
                    await sync_to_async(_save_bp_empty)(bp)
                    stats["empty"] += 1
                    continue

                listing_key = (bp.marketplace_slug, bp.external_id)
                listing_info = listing_map.get(listing_key)

                injected_count = await sync_to_async(_save_bp_filled)(
                    bp, result, listing_info
                )
                stats["points"] += injected_count
                if listing_info:
                    stats["injected"] += 1
                stats["filled"] += 1

                if (i + 1) % 200 == 0:
                    logger.info(
                        "  Phase 2: %d/%d — %d filled (%s points), %d injected, %d empty, %d failed",
                        i + 1,
                        total,
                        stats["filled"],
                        f"{stats['points']:,}",
                        stats["injected"],
                        stats["empty"],
                        stats["failed"],
                    )

            except Exception as e:
                await sync_to_async(_save_bp_failed)(bp, str(e))
                stats["failed"] += 1

    logger.info("Phase 2 complete: %s", stats)
    return stats
