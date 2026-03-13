"""Phase 3: Extend top products with PriceHistory.app deep history.

For BH-filled (or optionally discovered) BackfillProducts that have a
ph_code, fetch full 3-5 year price history from PriceHistory.app's
authenticated API. This extends backwards from the ~17 months BuyHatke
provides.

The PH flow is two-step per product:
  1. Fetch HTML page → extract per-page auth token
  2. POST /api/price/{code} with token → get full history + sale events

Includes:
- Retry with exponential backoff on 403/429
- Alternating cooldown pauses (15s/30s every 3 min)
- Wave-based processing (50 at a time) for data safety on cancel
- Rate-limited products released back for retry (not marked FAILED)
- Optional --include-discovered to skip bh-fill

Products are prioritized by those with existing listings (injected first)
and highest data point counts.

Supports parallel workers: uses ``SELECT ... FOR UPDATE SKIP LOCKED`` so
multiple nodes can run ``ph-extend`` simultaneously without overlap.

Usage::

    python manage.py backfill_prices ph-extend --limit 5000
    python manage.py backfill_prices ph-extend --marketplace amazon-in
    python manage.py backfill_prices ph-extend --include-discovered
"""
from __future__ import annotations

import asyncio
import logging

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import transaction
from django.db.models import F, Q

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.backfill.ph_client import AuthError, PHClient, RateLimitError
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)

# Process this many products per wave before checking for interrupts
_WAVE_SIZE = 50


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
    include_discovered: bool = False,
) -> tuple[list[str], dict[str, str]]:
    """Atomically claim a batch of products for this worker.

    Uses SELECT ... FOR UPDATE SKIP LOCKED to prevent overlap between
    parallel workers. Claimed items get status='ph_extending' so they
    won't appear in other workers' queries.

    Args:
        include_discovered: If True, also claim DISCOVERED products
            (skip bh-fill, go directly to ph-extend).

    Returns:
        Tuple of (claimed_ids, original_status_map) where original_status_map
        maps product ID → original status string before claiming.
    """
    db = _write_db()

    with transaction.atomic(using=db):
        status_filter = Q(status=BackfillProduct.Status.BH_FILLED)
        if include_discovered:
            status_filter |= Q(status=BackfillProduct.Status.DISCOVERED)

        qs = BackfillProduct.objects.using(db).filter(
            status_filter,
        ).exclude(
            ph_code="",
        )

        if marketplace_slug:
            qs = qs.filter(marketplace_slug=marketplace_slug)

        if category_names:
            qs = qs.filter(category_name__in=category_names)

        # Prioritize: products with existing listings first, then by data point count
        # Fetch id + status so we can record original status before overwriting
        claimed_rows = list(
            qs.order_by(
                F("product_listing_id").asc(nulls_last=True),
                "-price_data_points",
                "created_at",
            )
            .select_for_update(skip_locked=True)
            .values_list("id", "status")[:limit]
        )

        claimed_ids = [row[0] for row in claimed_rows]
        original_status_map = {row[0]: row[1] for row in claimed_rows}

        if claimed_ids:
            BackfillProduct.objects.using(db).filter(id__in=claimed_ids).update(
                status=BackfillProduct.Status.PH_EXTENDING
            )

    return claimed_ids, original_status_map


def _load_batch_and_listings(claimed_ids: list[str]) -> tuple[list, dict]:
    """Load claimed BackfillProducts and pre-fetch matching listings."""
    from apps.products.models import ProductListing

    db = _write_db()
    batch = list(BackfillProduct.objects.using(db).filter(id__in=claimed_ids))

    listing_map: dict[tuple[str, str], dict] = {}
    if batch:
        external_pairs = [
            (bp.marketplace_slug, bp.external_id)
            for bp in batch if bp.external_id
        ]
        for listing in ProductListing.objects.using(db).filter(
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
    db = _write_db()
    try:
        listing = ProductListing.objects.using(db).select_related("marketplace").get(id=listing_id)
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


def _save_bp_token_failed(bp, error_msg, revert_status: str | None = None):
    """Synchronous save for token extraction failure.

    Reverts status to original (BH_FILLED or DISCOVERED) so the product
    can be retried.
    """
    bp.status = revert_status or BackfillProduct.Status.BH_FILLED
    bp.error_message = error_msg[:500]
    bp.retry_count += 1
    bp.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


def _save_bp_rate_limited(bp, error_msg, revert_status: str | None = None):
    """Release a rate-limited product back for retry (NOT failed).

    Reverts to original status (BH_FILLED or DISCOVERED).
    """
    bp.status = revert_status or BackfillProduct.Status.BH_FILLED
    bp.error_message = error_msg[:500]
    bp.save(update_fields=["status", "error_message", "updated_at"])


def _save_bp_failed(bp, error_msg):
    """Synchronous save for API failure (non-rate-limit)."""
    bp.status = BackfillProduct.Status.FAILED
    bp.error_message = error_msg[:500]
    bp.retry_count += 1
    bp.save(update_fields=["status", "error_message", "retry_count", "updated_at"])


def _release_unclaimed(
    claimed_ids: list[str],
    processed_ids: set[str],
    original_status_map: dict[str, str] | None = None,
) -> int:
    """Release any claimed items that weren't processed back to their original status.

    Only releases items still in PH_EXTENDING status (items that were
    saved with another status like PH_EXTENDED won't be touched).

    Uses original_status_map to revert each product to its correct
    pre-claim status (BH_FILLED or DISCOVERED).
    """
    unprocessed = set(claimed_ids) - processed_ids
    if not unprocessed:
        return 0

    db = _write_db()
    total_released = 0

    if original_status_map:
        # Group by original status for efficient bulk updates
        by_status: dict[str, list[str]] = {}
        for bp_id in unprocessed:
            orig = original_status_map.get(bp_id, BackfillProduct.Status.BH_FILLED)
            by_status.setdefault(orig, []).append(bp_id)

        for status, ids in by_status.items():
            count = BackfillProduct.objects.using(db).filter(
                id__in=ids, status=BackfillProduct.Status.PH_EXTENDING
            ).update(status=status)
            if count:
                logger.warning(
                    "Released %d unclaimed ph_extending items back to %s", count, status,
                )
                total_released += count
    else:
        # Fallback: no map available, default to BH_FILLED
        total_released = BackfillProduct.objects.using(db).filter(
            id__in=list(unprocessed), status=BackfillProduct.Status.PH_EXTENDING
        ).update(status=BackfillProduct.Status.BH_FILLED)
        if total_released:
            logger.warning("Released %d unclaimed ph_extending items back to bh_filled", total_released)

    return total_released


async def extend_with_pricehistory(
    limit: int | None = None,
    marketplace_slug: str | None = None,
    delay: float | None = None,
    category_names: list[str] | None = None,
    include_discovered: bool = False,
    proxy_mode: str = "auto",
    worker_tag: str = "",
) -> dict:
    """Phase 3: Extend products with PH deep history.

    Processes products in waves of 50 for data safety. Each wave runs
    concurrently (semaphore-limited), and all saves complete before the
    next wave starts. On cancel/interrupt, only the current wave's
    in-progress items may be lost — all previous waves are persisted.

    Rate-limited products are released back to BH_FILLED for retry
    instead of being marked FAILED.

    Args:
        limit: Max products to process in this run.
        marketplace_slug: Filter by marketplace slug.
        delay: Override PH request delay.
        category_names: Filter by category names.
        include_discovered: Also claim DISCOVERED products (skip bh-fill).
        proxy_mode: "auto" (default), "proxy" (always proxy), "direct" (no proxy).

    Returns:
        Stats dict with counts including ``stop_requested`` flag.
    """
    limit = limit or BackfillConfig.phase3_limit()

    # Generate a short tag to identify this worker in logs
    if not worker_tag:
        import secrets
        worker_tag = secrets.token_hex(3)  # e.g. "a1b2c3"
    tag = f"[W-{worker_tag}]"

    # Atomically claim a batch — other workers will skip these rows
    claimed_ids, original_status_map = await sync_to_async(_claim_batch)(
        limit, marketplace_slug, category_names, include_discovered
    )

    if not claimed_ids:
        msg = "no products to extend (or all claimed by other workers)"
        if include_discovered:
            msg = "no BH_FILLED or DISCOVERED products to extend"
        logger.info("Phase 3 %s: %s", tag, msg)
        return {
            "total": 0, "extended": 0, "injected": 0,
            "token_failed": 0, "api_failed": 0, "rate_limited": 0,
            "points": 0,
        }

    # Load full objects + listings for claimed batch
    batch, listing_map = await sync_to_async(_load_batch_and_listings)(claimed_ids)
    total = len(batch)

    logger.info(
        "Phase 3 %s: PH deep extend for %d products (claimed from pool%s)",
        tag, total, ", includes discovered" if include_discovered else "",
    )
    stats = {
        "total": total, "extended": 0, "injected": 0,
        "token_failed": 0, "api_failed": 0, "rate_limited": 0,
        "points": 0,
    }
    processed_ids: set[str] = set()
    _done_count = 0
    _stop_requested = False

    async def _process_one(bp, client):
        """Fetch token + history for one product."""
        nonlocal _done_count, _stop_requested
        # Look up the original status so we revert correctly on failure
        revert_status = original_status_map.get(bp.id, BackfillProduct.Status.BH_FILLED)

        # If another product in this wave already triggered stop, skip immediately
        if _stop_requested:
            await sync_to_async(_save_bp_rate_limited)(
                bp, "Skipped — IP burned / rate limited", revert_status
            )
            stats["rate_limited"] += 1
            processed_ids.add(bp.id)
            _done_count += 1
            return

        try:
            # Step 1: Fetch HTML page for token
            meta = await client.fetch_page_metadata(bp.ph_code)
            token = meta.get("token", "")

            if not token:
                await sync_to_async(_save_bp_token_failed)(
                    bp, "No token extracted from HTML", revert_status
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

        except RateLimitError as e:
            # Release back for retry — NOT failed
            await sync_to_async(_save_bp_rate_limited)(bp, str(e), revert_status)
            stats["rate_limited"] += 1
            processed_ids.add(bp.id)
            # Only stop if no proxy configured — rotating proxy never exhausts
            # (each request gets a new IP, so just keep going)
            if not client._proxy_strategy.enabled:
                _stop_requested = True

        except AuthError as e:
            await sync_to_async(_save_bp_token_failed)(bp, f"Auth: {e}", revert_status)
            stats["token_failed"] += 1
            processed_ids.add(bp.id)

        except asyncio.CancelledError:
            # On cancel, release back — don't lose data
            await sync_to_async(_save_bp_rate_limited)(
                bp, "Cancelled during processing", revert_status
            )
            processed_ids.add(bp.id)
            raise

        except Exception as e:
            await sync_to_async(_save_bp_failed)(bp, str(e))
            stats["api_failed"] += 1
            processed_ids.add(bp.id)

        _done_count += 1
        if _done_count % 100 == 0:
            logger.info(
                "  Phase 3 %s: %d/%d — %d extended (%s points), %d injected, "
                "%d token_failed, %d api_failed, %d rate_limited",
                tag, _done_count, total,
                stats["extended"], f"{stats['points']:,}",
                stats["injected"], stats["token_failed"],
                stats["api_failed"], stats["rate_limited"],
            )

    try:
        async with PHClient(delay=delay, proxy_mode=proxy_mode) as client:
            # Process in waves for data safety
            for wave_start in range(0, total, _WAVE_SIZE):
                if _stop_requested:
                    proxy_info = f" (proxy: {client.stats.get('proxy', {})})" if client._proxy_strategy.enabled else ""
                    logger.warning(
                        "Phase 3 %s: stopping early due to rate limiting%s "
                        "(wave %d/%d, %d processed so far)",
                        tag, proxy_info,
                        wave_start // _WAVE_SIZE + 1,
                        (total + _WAVE_SIZE - 1) // _WAVE_SIZE,
                        _done_count,
                    )
                    break

                wave = batch[wave_start:wave_start + _WAVE_SIZE]
                tasks = [_process_one(bp, client) for bp in wave]

                # Wait for entire wave to complete before next wave
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Check for CancelledError in results
                for r in results:
                    if isinstance(r, asyncio.CancelledError):
                        raise r

                # Log wave completion
                wave_num = wave_start // _WAVE_SIZE + 1
                total_waves = (total + _WAVE_SIZE - 1) // _WAVE_SIZE
                logger.info(
                    "  Phase 3 %s: wave %d/%d complete (%d/%d processed)",
                    tag, wave_num, total_waves, _done_count, total,
                )

    except (KeyboardInterrupt, asyncio.CancelledError):
        logger.warning(
            "Phase 3 %s: interrupted after %d/%d products. "
            "All completed products are saved.",
            tag, _done_count, total,
        )
    finally:
        # Release any items we claimed but didn't process (e.g. crash/interrupt)
        released = await sync_to_async(_release_unclaimed)(
            claimed_ids, processed_ids, original_status_map
        )
        if released:
            stats["released_back"] = released

    stats["stop_requested"] = _stop_requested
    stats["worker_tag"] = worker_tag
    logger.info("Phase 3 %s complete: %s", tag, stats)
    return stats
