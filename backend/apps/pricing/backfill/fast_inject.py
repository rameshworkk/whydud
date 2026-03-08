"""COPY-based fast price snapshot injection.

Uses PostgreSQL COPY protocol for 5-10x faster bulk loads compared to
INSERT. Designed for injecting millions of price snapshots from the
backfill pipeline.

Compatible with psycopg3 (Django 5 default PostgreSQL backend).

Usage::

    from apps.pricing.backfill.fast_inject import copy_inject_snapshots

    rows = [
        (datetime_iso, listing_uuid, product_uuid, marketplace_id,
         '64999.00', None, None, True, '', 'buyhatke'),
        ...
    ]
    inserted = copy_inject_snapshots(rows)
"""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from django.db import connection

from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)

# Columns in price_snapshots table for COPY
_COPY_COLUMNS = (
    "time", "listing_id", "product_id", "marketplace_id",
    "price", "mrp", "discount_pct", "in_stock", "seller_name", "source",
)

_COPY_SQL = (
    "COPY price_snapshots "
    "(time, listing_id, product_id, marketplace_id, "
    "price, mrp, discount_pct, in_stock, seller_name, source) "
    "FROM STDIN"
)


def copy_inject_snapshots(rows: list[tuple]) -> int:
    """Insert price snapshots using PostgreSQL COPY protocol.

    5-10x faster than INSERT for bulk loads. Each row is a tuple of:
        (time, listing_id, product_id, marketplace_id,
         price, mrp, discount_pct, in_stock, seller_name, source)

    Uses psycopg3 ``cursor.copy()`` context manager.

    Args:
        rows: List of tuples matching the column order above.

    Returns:
        Number of rows written.
    """
    if not rows:
        return 0

    connection.ensure_connection()
    raw_conn = connection.connection

    with raw_conn.cursor() as cur:
        with cur.copy(_COPY_SQL) as copy:
            for row in rows:
                copy.write_row(row)

    return len(rows)


def batch_inject_from_backfill(batch_size: int = 5000) -> dict:
    """Process BackfillProduct records and inject their price history via COPY.

    Targets records that have a linked ProductListing but whose price data
    hasn't been fully injected yet. Uses COPY protocol for maximum throughput.

    Args:
        batch_size: Max BackfillProduct records to process per call.

    Returns:
        Stats dict: {processed, rows_injected, skipped, errors}
    """
    from apps.products.models import ProductListing

    # Find candidates: have linked listing + non-empty price data
    # Use status done/bh_filled/ph_extended to catch records at any stage
    candidates = list(
        BackfillProduct.objects.filter(
            product_listing__isnull=False,
        )
        .exclude(raw_price_data=[])
        .select_related("product_listing__marketplace")
        .order_by("created_at")[:batch_size]
    )

    if not candidates:
        logger.info("batch_inject_from_backfill: no candidates found")
        return {"processed": 0, "rows_injected": 0, "skipped": 0, "errors": 0}

    logger.info(
        "batch_inject_from_backfill: gathering rows from %d BackfillProducts",
        len(candidates),
    )

    stats = {"processed": 0, "rows_injected": 0, "skipped": 0, "errors": 0}

    # Pre-check which listings already have data (skip fully-injected ones)
    listing_ids = [str(bp.product_listing_id) for bp in candidates]
    existing_counts: dict[str, int] = {}
    with connection.cursor() as cur:
        # Get count per listing+source to enable idempotent re-runs
        placeholders = ",".join(["%s"] * len(listing_ids))
        cur.execute(
            f"SELECT listing_id, source, COUNT(*) FROM price_snapshots "
            f"WHERE listing_id IN ({placeholders}) "
            f"GROUP BY listing_id, source",
            listing_ids,
        )
        for row in cur.fetchall():
            key = f"{row[0]}:{row[1]}"
            existing_counts[key] = row[2]

    # Gather all rows to inject
    all_rows: list[tuple] = []
    for bp in candidates:
        listing = bp.product_listing
        if not listing:
            stats["skipped"] += 1
            continue

        try:
            listing_id = str(listing.id)
            product_id = str(listing.product_id)
            marketplace_id = listing.marketplace_id

            # Group by source to check existing counts
            by_source: dict[str, list[dict]] = {}
            for entry in bp.raw_price_data:
                source = entry.get("s", "backfill")
                by_source.setdefault(source, []).append(entry)

            bp_rows: list[tuple] = []
            for source, entries in by_source.items():
                # Skip if already fully injected for this source
                existing_key = f"{listing_id}:{source}"
                if existing_counts.get(existing_key, 0) >= len(entries):
                    continue

                for entry in entries:
                    time_val = entry.get("t")
                    price_val = entry.get("p")
                    if not time_val or not price_val:
                        continue

                    try:
                        price_dec = Decimal(str(price_val))
                        if price_dec <= 0:
                            continue
                    except InvalidOperation:
                        continue

                    bp_rows.append((
                        time_val,
                        listing_id,
                        product_id,
                        marketplace_id,
                        str(price_dec),
                        None,    # mrp
                        None,    # discount_pct
                        True,    # in_stock
                        "",      # seller_name
                        source,
                    ))

            all_rows.extend(bp_rows)
            stats["processed"] += 1

        except Exception:
            logger.exception(
                "Error gathering rows for %s/%s",
                bp.marketplace_slug, bp.external_id,
            )
            stats["errors"] += 1

    # Inject all rows in one COPY call
    if all_rows:
        try:
            injected = copy_inject_snapshots(all_rows)
            stats["rows_injected"] = injected
            logger.info(
                "batch_inject_from_backfill: injected %s rows via COPY",
                f"{injected:,}",
            )
        except Exception:
            logger.exception("COPY injection failed for %d rows", len(all_rows))
            stats["errors"] += 1
    else:
        logger.info("batch_inject_from_backfill: no new rows to inject (all up-to-date)")

    logger.info("batch_inject_from_backfill complete: %s", stats)
    return stats
