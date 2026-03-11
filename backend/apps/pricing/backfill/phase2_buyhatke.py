"""Phase 2: Bulk price history fill from BuyHatke.

For every discovered product (from Phase 1) with an ASIN/FSID,
call BuyHatke's open API to get ~17 months of price history.

For products that match an existing ProductListing, price points
are injected directly into ``price_snapshots``. Products without
a matching listing still get their metadata updated (point count,
predictions) so Phase 4 can re-run injection after spider enrichment.

Speed: ~120 products/minute with default settings (0.5s delay, 5 concurrent).

Supports parallel workers: uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so
multiple nodes can run ``bh-fill`` simultaneously without overlap.

Usage::

    python manage.py backfill_prices bh-fill --batch 5000
    python manage.py backfill_prices bh-fill --marketplace amazon-in
"""
from __future__ import annotations

import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction

from apps.pricing.backfill.bh_client import BHClient, BHRateLimited
from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


def _write_db() -> str:
    """Return the database alias for write operations.

    On replica nodes, 'write' points to primary via WireGuard.
    On primary nodes (or dev), falls back to 'default'.
    """
    return "write" if "write" in settings.DATABASES else "default"


def _claim_batch(
    batch_size: int,
    marketplace_slug: str | None,
    category_names: list[str] | None = None,
) -> list[str]:
    """Atomically claim a batch of DISCOVERED products for this worker.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent overlap between
    parallel workers. Claimed items get status='bh_filling' so they
    won't appear in other workers' queries.

    Routes to the write database so this works on replica nodes too.

    Returns list of claimed BackfillProduct IDs.
    """
    supported_slugs = list(BackfillConfig.bh_pos_map().keys())
    db = _write_db()

    with transaction.atomic(using=db):
        qs = BackfillProduct.objects.using(db).filter(
            status=BackfillProduct.Status.DISCOVERED,
        ).exclude(
            external_id="",
        ).filter(
            marketplace_slug__in=supported_slugs,
        )

        if marketplace_slug:
            qs = qs.filter(marketplace_slug=marketplace_slug)

        if category_names:
            qs = qs.filter(category_name__in=category_names)

        # select_for_update(skip_locked=True) skips rows locked by other workers
        claimed_ids = list(
            qs.order_by("created_at")
            .select_for_update(skip_locked=True)
            .values_list("id", flat=True)[:batch_size]
        )

        if claimed_ids:
            BackfillProduct.objects.using(db).filter(id__in=claimed_ids).update(
                status=BackfillProduct.Status.BH_FILLING
            )

    return claimed_ids


def _load_batch_and_listings(claimed_ids: list[str]) -> tuple[list, dict]:
    """Load claimed BackfillProducts and pre-fetch matching listings."""
    from apps.products.models import ProductListing

    batch = list(BackfillProduct.objects.filter(id__in=claimed_ids))

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

    # Always cache raw data for later injection
    bp.append_price_data(result.price_points, source="buyhatke")

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


def _release_bp_rate_limited(bp):
    """Release a rate-limited product back to DISCOVERED for another node to pick up."""
    db = _write_db()
    BackfillProduct.objects.using(db).filter(
        id=bp.id, status=BackfillProduct.Status.BH_FILLING
    ).update(status=BackfillProduct.Status.DISCOVERED)


def _release_unclaimed(claimed_ids: list[str], processed_ids: set[str]) -> int:
    """Release any claimed items that weren't processed (e.g. worker crash recovery).

    Resets them back to DISCOVERED so they can be picked up again.
    """
    unprocessed = set(claimed_ids) - processed_ids
    if unprocessed:
        db = _write_db()
        count = BackfillProduct.objects.using(db).filter(
            id__in=list(unprocessed), status=BackfillProduct.Status.BH_FILLING
        ).update(status=BackfillProduct.Status.DISCOVERED)
        if count:
            logger.warning("Released %d unclaimed bh_filling items back to discovered", count)
        return count
    return 0


async def buyhatke_bulk_fill(
    batch_size: int | None = None,
    marketplace_slug: str | None = None,
    delay: float | None = None,
    category_names: list[str] | None = None,
) -> dict:
    """Phase 2: For all discovered products, fetch BuyHatke price history.

    Uses SELECT ... FOR UPDATE SKIP LOCKED for safe parallel execution
    across multiple worker nodes. Processes products concurrently via
    asyncio.gather() with semaphore-based rate limiting.

    Args:
        batch_size: Max products to process in this run.
        marketplace_slug: Filter by marketplace slug.
        delay: Override BH request delay.
        category_names: Filter by category names (e.g. ['smartphone', 'laptop']).

    Returns:
        Stats dict with counts.
    """
    batch_size = batch_size or BackfillConfig.phase2_batch_size()

    # Atomically claim a batch — other workers will skip these rows
    claimed_ids = await sync_to_async(_claim_batch)(batch_size, marketplace_slug, category_names)

    if not claimed_ids:
        logger.info("Phase 2: no discovered products to fill (or all claimed by other workers)")
        return {"total": 0, "filled": 0, "injected": 0, "empty": 0, "failed": 0, "points": 0}

    # Load full objects + listings for claimed batch
    batch, listing_map = await sync_to_async(_load_batch_and_listings)(claimed_ids)
    total = len(batch)

    logger.info("Phase 2: BuyHatke bulk fill for %d products (claimed from pool)", total)
    stats = {"total": total, "filled": 0, "injected": 0, "empty": 0, "failed": 0, "rate_limited": 0, "points": 0}
    processed_ids: set[str] = set()
    _done_count = 0

    async def _process_one(bp, client):
        """Fetch + save one product. Semaphore inside BHClient limits concurrency."""
        nonlocal _done_count
        try:
            result = await client.fetch_price_history(
                pid=bp.external_id,
                marketplace_slug=bp.marketplace_slug,
            )

            if not result.found or result.point_count == 0:
                await sync_to_async(_save_bp_empty)(bp)
                stats["empty"] += 1
                processed_ids.add(bp.id)
            else:
                listing_key = (bp.marketplace_slug, bp.external_id)
                listing_info = listing_map.get(listing_key)

                injected_count = await sync_to_async(_save_bp_filled)(
                    bp, result, listing_info
                )
                stats["points"] += injected_count
                if listing_info:
                    stats["injected"] += 1
                stats["filled"] += 1
                processed_ids.add(bp.id)

        except BHRateLimited:
            # Rate limited — release back to pool for another node/retry
            await sync_to_async(_release_bp_rate_limited)(bp)
            stats["rate_limited"] += 1
            processed_ids.add(bp.id)

        except Exception as e:
            await sync_to_async(_save_bp_failed)(bp, str(e))
            stats["failed"] += 1
            processed_ids.add(bp.id)

        _done_count += 1
        if _done_count % 200 == 0:
            logger.info(
                "  Phase 2: %d/%d — %d filled (%s points), %d injected, %d empty, %d failed, %d rate_limited",
                _done_count, total,
                stats["filled"], f"{stats['points']:,}",
                stats["injected"], stats["empty"], stats["failed"], stats["rate_limited"],
            )

    try:
        async with BHClient(delay=delay) as client:
            # Fire all tasks concurrently — BHClient semaphore limits to N in-flight
            tasks = [_process_one(bp, client) for bp in batch]
            await asyncio.gather(*tasks)
    finally:
        # Release any items we claimed but didn't process (e.g. crash/interrupt)
        await sync_to_async(_release_unclaimed)(claimed_ids, processed_ids)

    logger.info("Phase 2 complete: %s", stats)
    return stats
