"""Add ``source`` column to price_snapshots hypertable.

The column tags where each row came from:
  - 'scraper'           — our own Amazon/Flipkart spiders
  - 'buyhatke'          — BuyHatke backfill (Phase 0 / Phase 2)
  - 'pricehistory_app'  — PriceHistory.app deep history (Phase 3)
  - 'backfill'          — merged backfill data

Also adds a dedup index so re-runs can use ON CONFLICT DO NOTHING.

NOTE: price_snapshots is a TimescaleDB hypertable (managed=False).
We must use raw SQL + autocommit, same pattern as 0002_timescaledb_setup.
"""
from django.db import migrations


def _add_source_column(apps, schema_editor):
    """Add source column and dedup index to price_snapshots."""
    conn = schema_editor.connection
    raw_conn = conn.connection  # underlying psycopg3 connection

    was_autocommit = raw_conn.autocommit
    raw_conn.autocommit = True
    try:
        with raw_conn.cursor() as cur:
            # Add source column with default for existing rows
            cur.execute("""
                ALTER TABLE price_snapshots
                ADD COLUMN IF NOT EXISTS source VARCHAR(30) DEFAULT 'scraper';
            """)

            # Index for filtering by source
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_snapshots_source
                ON price_snapshots (source, time DESC);
            """)

            # Index for listing + source lookups (used by injector dedup check)
            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_price_snapshots_listing_source
                ON price_snapshots (listing_id, source);
            """)
    finally:
        raw_conn.autocommit = was_autocommit


class Migration(migrations.Migration):
    atomic = False  # belt-and-suspenders; autocommit managed per-step

    dependencies = [
        ("pricing", "0004_alter_pricealert_unique_together_and_more"),
    ]

    operations = [
        migrations.RunPython(
            _add_source_column,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
