"""Phase 0: Instant backfill for existing ProductListings via BuyHatke.

For products already in our database, skip the staging table and inject
BuyHatke price history directly into ``price_snapshots``.

This is the quickest path to value — existing products get 17-month
price charts with zero staging overhead.

Usage::

    python manage.py backfill_prices existing --marketplace amazon-in --limit 500
"""
from __future__ import annotations

import logging

from asgiref.sync import sync_to_async
from django.db import connection

from apps.pricing.backfill.bh_client import BHClient
from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.injector import inject_price_points

logger = logging.getLogger(__name__)


def _query_eligible_listings(
    marketplace_slug: str | None, limit: int
) -> list:
    """Synchronous ORM query for eligible listings."""
    from apps.products.models import ProductListing

    supported_slugs = list(BackfillConfig.bh_pos_map().keys())
    qs = ProductListing.objects.filter(
        marketplace__slug__in=supported_slugs,
    ).exclude(
        external_id="",
    ).select_related("marketplace", "product")

    if marketplace_slug:
        qs = qs.filter(marketplace__slug=marketplace_slug)

    # Skip listings already backfilled from BuyHatke
    already_done: set[str] = set()
    with connection.cursor() as cur:
        cur.execute(
            "SELECT DISTINCT listing_id::text FROM price_snapshots WHERE source = 'buyhatke'"
        )
        already_done = {row[0] for row in cur.fetchall()}

    # Order by most reviewed products first (highest value)
    listings = []
    for listing in qs.order_by("-product__total_reviews")[:limit + len(already_done)]:
        if str(listing.id) not in already_done:
            listings.append(listing)
        if len(listings) >= limit:
            break

    return listings


async def backfill_existing_listings(
    marketplace_slug: str | None = None,
    limit: int | None = None,
    delay: float | None = None,
    dry_run: bool = False,
) -> dict:
    """Backfill price history for existing ProductListings via BuyHatke.

    Args:
        marketplace_slug: Filter by marketplace (e.g. ``"amazon-in"``).
        limit: Max listings to process.
        delay: Override default BH request delay.
        dry_run: If True, fetch data but don't insert into DB.

    Returns:
        Stats dict with counts.
    """
    limit = limit or BackfillConfig.phase0_batch_size()

    listings = await sync_to_async(_query_eligible_listings)(marketplace_slug, limit)

    total = len(listings)
    if total == 0:
        logger.info("Phase 0: no eligible listings to backfill")
        return {"total": 0, "filled": 0, "empty": 0, "failed": 0, "points": 0}

    logger.info(
        "Phase 0: BuyHatke backfill for %d existing listings (dry_run=%s)",
        total,
        dry_run,
    )
    stats = {"total": total, "filled": 0, "empty": 0, "failed": 0, "points": 0}

    async with BHClient(delay=delay) as client:
        for i, listing in enumerate(listings):
            try:
                result = await client.fetch_price_history(
                    pid=listing.external_id,
                    marketplace_slug=listing.marketplace.slug,
                )

                if not result.found or result.point_count == 0:
                    stats["empty"] += 1
                    continue

                if not dry_run:
                    count = await sync_to_async(inject_price_points)(
                        listing_id=str(listing.id),
                        product_id=str(listing.product_id),
                        marketplace_id=listing.marketplace_id,
                        price_points=result.price_points,
                        source="buyhatke",
                    )
                    stats["points"] += count
                else:
                    stats["points"] += result.point_count

                stats["filled"] += 1

                if (i + 1) % 100 == 0:
                    logger.info(
                        "  Phase 0: %d/%d — %d filled (%s points), %d empty, %d failed",
                        i + 1,
                        total,
                        stats["filled"],
                        f"{stats['points']:,}",
                        stats["empty"],
                        stats["failed"],
                    )

            except Exception as e:
                stats["failed"] += 1
                logger.warning(
                    "  Phase 0 [%s/%s]: %s",
                    listing.marketplace.slug,
                    listing.external_id,
                    str(e)[:200],
                )

    logger.info("Phase 0 complete: %s", stats)
    return stats
