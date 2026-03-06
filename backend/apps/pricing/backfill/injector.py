"""Bulk insert price points into the price_snapshots TimescaleDB hypertable.

Shared by all backfill phases. Uses raw SQL with parameterized queries
for efficient batch insertion. Uses ``ON CONFLICT DO NOTHING`` via
a pre-check (count existing rows) for idempotent re-runs.

All prices must already be in paisa. All timestamps must be UTC.
"""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import connection

from apps.pricing.backfill.config import BackfillConfig

logger = logging.getLogger(__name__)


def inject_price_points(
    listing_id: str,
    product_id: str,
    marketplace_id: int,
    price_points: list,
    source: str,
    batch_size: int | None = None,
) -> int:
    """Insert price points into ``price_snapshots``. Returns count inserted.

    Args:
        listing_id: UUID of the ProductListing.
        product_id: UUID of the Product.
        marketplace_id: Integer PK of the Marketplace.
        price_points: List of objects with ``.time`` and ``.price`` attrs,
            or dicts with ``time`` and ``price`` keys. Prices in paisa, times in UTC.
        source: Data source tag (``'buyhatke'``, ``'pricehistory_app'``, ``'backfill'``).
        batch_size: Rows per INSERT batch. Defaults to config value.

    Returns:
        Total rows successfully inserted.
    """
    if not price_points:
        return 0

    batch_size = batch_size or BackfillConfig.inject_batch_size()

    # Pre-check: skip if listing already has enough rows from this source
    with connection.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM price_snapshots WHERE listing_id = %s AND source = %s",
            [listing_id, source],
        )
        existing_count = cur.fetchone()[0]

    if existing_count >= len(price_points):
        return 0

    # Build valid tuples
    valid: list[tuple] = []
    for pt in price_points:
        # Support both dataclass (PricePoint) and dict
        if hasattr(pt, "time"):
            time_val = pt.time
            price_val = pt.price
            mrp_val = getattr(pt, "mrp", None)
        else:
            time_val = pt.get("time")
            price_val = pt.get("price")
            mrp_val = pt.get("mrp")

        if not time_val or not price_val:
            continue

        price_dec = Decimal(str(price_val)) if not isinstance(price_val, Decimal) else price_val
        if price_dec <= 0:
            continue

        valid.append((
            time_val,
            listing_id,
            product_id,
            marketplace_id,
            str(price_dec),
            str(mrp_val) if mrp_val else None,
            None,       # discount_pct
            True,       # in_stock
            "",         # seller_name
            source,
        ))

    if not valid:
        return 0

    inserted = 0
    for i in range(0, len(valid), batch_size):
        batch = valid[i : i + batch_size]
        placeholders = ", ".join(["(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"] * len(batch))
        flat = [v for tup in batch for v in tup]

        with connection.cursor() as cur:
            cur.execute(
                f"""
                INSERT INTO price_snapshots
                    (time, listing_id, product_id, marketplace_id,
                     price, mrp, discount_pct, in_stock, seller_name, source)
                VALUES {placeholders}
                ON CONFLICT DO NOTHING
                """,
                flat,
            )
            inserted += cur.rowcount

    return inserted


def count_snapshots_by_source() -> dict[str, int]:
    """Return row counts per source tag in price_snapshots."""
    with connection.cursor() as cur:
        cur.execute("SELECT source, COUNT(*) FROM price_snapshots GROUP BY source ORDER BY source")
        return {row[0] or "unknown": row[1] for row in cur.fetchall()}
