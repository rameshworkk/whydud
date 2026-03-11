"""Phase 3: Extend top products with PriceHistory.app deep history.

For BH-filled BackfillProducts that have a ph_code, fetch full 3-5 year
price history from PriceHistory.app's authenticated API. This extends
backwards from the ~17 months BuyHatke provides.

The PH flow is two-step per product:
  1. Fetch HTML page → extract per-page auth token
  2. POST /api/price/{code} with token → get full history + sale events

Rate limits are stricter than BuyHatke (Cloudflare protection), so we
use a slower default: 4s API delay, 3 concurrent requests.

Products are prioritized by those with existing listings (injected first)
and highest data point counts.

Supports parallel workers: uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so
multiple nodes can run ``ph-extend`` simultaneously without overlap.

Usage::

    python manage.py backfill_prices ph-extend --limit 5000
    python manage.py backfill_prices ph-extend --marketplace amazon-in
"""
from __future__ import annotations

import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.db.models import F

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.backfill.ph_client import AuthError, PHClient
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


def _write_db() -> str:
    """Return the database alias for write operations.

    On replica nodes, 'write' points to primary via WireGuard.
    On primary nodes (or dev), falls back to 'default'.
    """
    return "write" if "write" in settings.DATABASES else "default"


def _claim_batch(
    limit: int,
    marketplace_slug: str | None,
    category_names: list[str] | None = None,
) -> list[str]:
    """Atomically claim a batch of BH_FILLED products for this worker.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent overlap between
    parallel workers. Claimed items get status='ph_extending' so they
    won't appear in other workers' queries.

    Routes to the write database so this works on replica nodes too.

    Returns list of claimed BackfillProduct IDs.
    """
    db = _write_db()

    with transaction.atomic(using=db):
        qs = BackfillProduct.objects.using(db).filter(
            status=BackfillProduct.Status.BH_FILLED,
        ).exclude(
            ph_code="",
        )

        if marketplace_slug:
            qs = qs.filter(marketplace_slug=marketplace_slug)

        if category_names:
            qs = qs.filter(category_name__in=category_names)

        # Prioritize: products with existing listings first, then by data point count
        claimed_ids = list(
            qs.order_by(
                F("product_listing_id").asc(nulls_last=True),
                "-price_data_points",
                "created_at",
            )
            .select_for_update(skip_locked=True)
            .values_list("id", flat=True)[:limit]
        )

        if claimed_ids:
            BackfillProduct.objects.using(db).filter(id__in=claimed_ids).update(
                status=BackfillProduct.Status.PH_EXTENDING
            )

    return claimed_ids


def _load_batch_and_listings(claimed_ids: list[str]) -> tuple[list, dict]:
    """Load claimed BackfillProducts and pre-fetch matching listings."""
    from apps.products.models import ProductListing

    batch = list(BackfillProduct.objects.filter(id__in=claimed_ids))

    listing_map: dict[tuple[str, str], dict] = {}
    if batch:
        external_pairs = [
            (bp.marketplace_slug, bp.external_id)
            for bp in batch if bp.external_id
        ]
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


def _get_listing_by_id(listing_id):
    """Synchronous ORM query for a single listing."""
    from apps.products.models import ProductListing
    try:
        listing = ProductListing.objects.select_related("marketplace").get(id=listing_id)
        return {
            "listing_id": str(listing.id),
            "product_id": str(listing.product_id),
            "marketplace_id": listing.marketplace_id,
        }
    except ProductListing.DoesNotExist:
        return None


def _save_bp_extended(bp, result, listing_info):
    """Synchronous save for a successfully extended BackfillProduct."""
    price_points = result["price_points"]
    point_count = result.get("point_count", len(price_points))

    # Update metadata from PH
    summary = result.get("summary", {})
    if summary.get("min_price"):
        bp.min_price = summary["min_price"]
    if summary.get("max_price"):
        bp.max_price = summary["max_price"]
    if summary.get("min_date"):
        bp.min_price_date = summary["min_date"]
    if summary.get("max_date"):
        bp.max_price_date = summary["max_date"]

    # Always cache raw data for later injection (appends to BH cache)
    bp.append_price_data(price_points, source="pricehistory_app")

    # Update history range if PH extends beyond BH
    if price_points:
        first_time = price_points[0].time
        last_time = price_points[-1].time
        if not bp.history_from or first_time < bp.history_from:
            bp.history_from = first_time
        if not bp.history_to or last_time > bp.history_to:
            bp.history_to = last_time

    bp.price_data_points = (bp.price_data_points or 0) + point_count
    bp.status = BackfillProduct.Status.PH_EXTENDED
    bp.error_message = ""

    injected_count = 0
    if listing_info:
        injected_count = inject_price_points(
            listing_id=listing_info["listing_id"],
            product_id=listing_info["product_id"],
            marketplace_id=listing_info["marketplace_id"],
            price_points=price_points,
            source="pricehistory_app",
        )
        if not bp.product_listing_id:
            bp.product_listing_id = listing_info["listing_id"]

    bp.save()
    return injected_count


def _save_bp_empty(bp):
    """Synchronous save for empty PH result."""
    bp.status = BackfillProduct.Status.PH_EXTENDED
    bp.save(update_fields=["status", "updated_at"])


def _save_bp_token_failed(bp, error_msg):
    """Synchronous save for token extraction failure.

    Reverts status to BH_FILLED so the product can be retried.
    """
    bp.status = BackfillProduct.Status.BH_FILLED
    bp.error_message = error_msg[:500]
    bp.retry_count += 1
    bp.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


def _save_bp_failed(bp, error_msg):
    """Synchronous save for API failure."""
    bp.status = BackfillProduct.Status.FAILED
    bp.error_message = error_msg[:500]
    bp.retry_count += 1
    bp.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


def _release_unclaimed(claimed_ids: list[str], processed_ids: set[str]) -> int:
    """Release any claimed items that weren't processed back to BH_FILLED."""
    unprocessed = set(claimed_ids) - processed_ids
    if unprocessed:
        db = _write_db()
        count = BackfillProduct.objects.using(db).filter(
            id__in=list(unprocessed), status=BackfillProduct.Status.PH_EXTENDING
        ).update(status=BackfillProduct.Status.BH_FILLED)
        if count:
            logger.warning("Released %d unclaimed ph_extending items back to bh_filled", count)
        return count
    return 0


async def extend_with_pricehistory(
    limit: int | None = None,
    marketplace_slug: str | None = None,
    delay: float | None = None,
    category_names: list[str] | None = None,
) -> dict:
    """Phase 3: Extend BH-filled products with PH deep history.

    Uses SELECT ... FOR UPDATE SKIP LOCKED for safe parallel execution
    across multiple worker nodes. Processes products concurrently via
    asyncio.gather() with semaphore-based rate limiting.

    Args:
        limit: Max products to process in this run.
        marketplace_slug: Filter by marketplace slug.
        delay: Override PH request delay.
        category_names: Filter by category names (e.g. ['smartphone', 'laptop']).

    Returns:
        Stats dict with counts.
    """
    limit = limit or BackfillConfig.phase3_limit()

    # Atomically claim a batch — other workers will skip these rows
    claimed_ids = await sync_to_async(_claim_batch)(limit, marketplace_slug, category_names)

    if not claimed_ids:
        logger.info("Phase 3: no BH-filled products to extend (or all claimed by other workers)")
        return {
            "total": 0, "extended": 0, "injected": 0,
            "token_failed": 0, "api_failed": 0, "points": 0,
        }

    # Load full objects + listings for claimed batch
    batch, listing_map = await sync_to_async(_load_batch_and_listings)(claimed_ids)
    total = len(batch)

    logger.info("Phase 3: PH deep extend for %d products (claimed from pool)", total)
    stats = {
        "total": total, "extended": 0, "injected": 0,
        "token_failed": 0, "api_failed": 0, "points": 0,
    }
    processed_ids: set[str] = set()
    _done_count = 0

    async def _process_one(bp, client):
        """Fetch token + history for one product. Semaphore inside PHClient limits concurrency."""
        nonlocal _done_count
        try:
            # Step 1: Fetch HTML page for token
            meta = await client.fetch_page_metadata(bp.ph_code)
            token = meta.get("token", "")

            if not token:
                await sync_to_async(_save_bp_token_failed)(
                    bp, "No token extracted from HTML"
                )
                stats["token_failed"] += 1
                processed_ids.add(bp.id)
                _done_count += 1
                return

            # Step 2: Fetch full price history via API
            result = await client.fetch_price_history(bp.ph_code, token)

            if not result.get("price_points"):
                await sync_to_async(_save_bp_empty)(bp)
                stats["extended"] += 1
                processed_ids.add(bp.id)
                _done_count += 1
                return

            # Resolve listing info
            listing_key = (bp.marketplace_slug, bp.external_id)
            listing_info = listing_map.get(listing_key)

            # Also check product_listing_id set by Phase 2
            if not listing_info and bp.product_listing_id:
                listing_info = await sync_to_async(_get_listing_by_id)(
                    bp.product_listing_id
                )

            injected_count = await sync_to_async(_save_bp_extended)(
                bp, result, listing_info
            )
            stats["points"] += injected_count
            if listing_info:
                stats["injected"] += 1
            stats["extended"] += 1
            processed_ids.add(bp.id)

        except AuthError as e:
            await sync_to_async(_save_bp_token_failed)(bp, f"Auth: {e}")
            stats["token_failed"] += 1
            processed_ids.add(bp.id)

        except Exception as e:
            await sync_to_async(_save_bp_failed)(bp, str(e))
            stats["api_failed"] += 1
            processed_ids.add(bp.id)

        _done_count += 1
        if _done_count % 100 == 0:
            logger.info(
                "  Phase 3: %d/%d — %d extended (%s points), %d injected, "
                "%d token_failed, %d api_failed",
                _done_count, total,
                stats["extended"], f"{stats['points']:,}",
                stats["injected"], stats["token_failed"], stats["api_failed"],
            )

    try:
        async with PHClient(delay=delay) as client:
            # Fire all tasks concurrently — PHClient semaphore limits to N in-flight
            tasks = [_process_one(bp, client) for bp in batch]
            await asyncio.gather(*tasks)
    finally:
        # Release any items we claimed but didn't process (e.g. crash/interrupt)
        await sync_to_async(_release_unclaimed)(claimed_ids, processed_ids)

    logger.info("Phase 3 complete: %s", stats)
    return stats
