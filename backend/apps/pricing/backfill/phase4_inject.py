"""Phase 4: Inject cached price data into price_snapshots.

After marketplace spiders create ProductListings for discovered ASINs,
this phase matches BackfillProducts to their listings and injects the
cached raw_price_data without any external API calls.

This is fully synchronous — no async, no HTTP. Safe to run frequently.

Usage::

    python manage.py backfill_prices inject --batch 5000
    python manage.py backfill_prices inject --marketplace amazon-in --dry-run
"""
from __future__ import annotations

import logging
from datetime import datetime

from django.db.models import Q

from apps.pricing.backfill.injector import inject_price_points
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)


def inject_cached_data(
    batch_size: int = 5000,
    marketplace_slug: str | None = None,
    dry_run: bool = False,
) -> dict:
    """Phase 4: Inject cached price data for BackfillProducts with matching listings.

    Finds BackfillProducts that:
      - Have status bh_filled or ph_extended (not yet done)
      - Have non-empty raw_price_data
      - Have no linked product_listing_id (not yet injected)
      - Match an existing ProductListing by (marketplace_slug, external_id)

    Args:
        batch_size: Max products to process in this run.
        marketplace_slug: Filter by marketplace slug.
        dry_run: If True, find matches but don't inject.

    Returns:
        Stats dict with counts.
    """
    from apps.products.models import ProductListing

    # Find injectable candidates: have cached data, not yet DONE
    # Two paths:
    #   1. Listing already linked (from targeted scrape reconciliation)
    #   2. No listing yet — match by (marketplace_slug, external_id)
    base_qs = BackfillProduct.objects.filter(
        status__in=[
            BackfillProduct.Status.BH_FILLED,
            BackfillProduct.Status.PH_EXTENDED,
        ],
    ).exclude(
        raw_price_data=[],
    ).exclude(
        external_id="",
    )

    if marketplace_slug:
        base_qs = base_qs.filter(marketplace_slug=marketplace_slug)

    batch = list(base_qs.order_by("created_at")[:batch_size])
    total = len(batch)

    if total == 0:
        logger.info("Phase 4: no injectable candidates found")
        return {
            "total": 0, "matched": 0, "injected": 0,
            "points": 0, "no_listing": 0,
        }

    logger.info("Phase 4: checking %d candidates for matching listings", total)

    # Pre-fetch matching listings in bulk for products without linked listing
    unlinked = [bp for bp in batch if bp.product_listing_id is None]
    external_pairs = [
        (bp.marketplace_slug, bp.external_id) for bp in unlinked
    ]
    listing_map: dict[tuple[str, str], dict] = {}
    if external_pairs:
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

    # Pre-fetch listings already linked by scrape reconciliation
    linked_ids = [bp.product_listing_id for bp in batch if bp.product_listing_id is not None]
    linked_listing_map: dict[str, dict] = {}
    if linked_ids:
        for listing in ProductListing.objects.filter(
            id__in=linked_ids,
        ).select_related("marketplace"):
            linked_listing_map[str(listing.id)] = {
                "listing_id": str(listing.id),
                "product_id": str(listing.product_id),
                "marketplace_id": listing.marketplace_id,
            }

    stats = {
        "total": total,
        "matched": 0,
        "injected": 0,
        "points": 0,
        "no_listing": 0,
    }

    for i, bp in enumerate(batch):
        # Try already-linked listing first, then match by external_id
        if bp.product_listing_id:
            listing_info = linked_listing_map.get(str(bp.product_listing_id))
        else:
            listing_key = (bp.marketplace_slug, bp.external_id)
            listing_info = listing_map.get(listing_key)

        if not listing_info:
            stats["no_listing"] += 1
            continue

        stats["matched"] += 1

        if dry_run:
            stats["points"] += len(bp.raw_price_data)
            continue

        # Group cached points by source for separate injection
        by_source: dict[str, list[dict]] = {}
        for entry in bp.raw_price_data:
            source = entry.get("s", "backfill")
            by_source.setdefault(source, []).append({
                "time": entry["t"],
                "price": entry["p"],
            })

        total_injected = 0
        for source, points in by_source.items():
            count = inject_price_points(
                listing_id=listing_info["listing_id"],
                product_id=listing_info["product_id"],
                marketplace_id=listing_info["marketplace_id"],
                price_points=points,
                source=source,
            )
            total_injected += count

        # Update BackfillProduct
        bp.product_listing_id = listing_info["listing_id"]
        bp.status = BackfillProduct.Status.DONE
        bp.save(update_fields=["product_listing_id", "status", "updated_at"])

        stats["points"] += total_injected
        stats["injected"] += 1

        if (i + 1) % 200 == 0:
            logger.info(
                "  Phase 4: %d/%d — %d matched, %d injected (%s points), %d no listing",
                i + 1, total,
                stats["matched"], stats["injected"],
                f"{stats['points']:,}",
                stats["no_listing"],
            )

    logger.info("Phase 4 complete: %s", stats)
    return stats
