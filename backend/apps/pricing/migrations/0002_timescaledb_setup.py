"""Create the price_snapshots TimescaleDB hypertable and price_daily continuous aggregate.

PriceSnapshot is managed=False in Django (Django won't CREATE TABLE for it),
so we create the table and hypertable here manually.

NOTE: TimescaleDB continuous aggregates cannot run inside any transaction block,
even implicit ones.  We use RunPython + raw connection autocommit for that step.
"""
from django.db import migrations


def _create_price_table_and_hypertable(apps, schema_editor):
    """Create price_snapshots and convert it to a hypertable."""
    conn = schema_editor.connection
    raw_conn = conn.connection  # underlying psycopg3 connection

    was_autocommit = raw_conn.autocommit
    raw_conn.autocommit = True
    try:
        with raw_conn.cursor() as cur:
            # Ensure extensions exist (init.sql only runs on first volume
            # init — these are idempotent and cover re-deploys).
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            cur.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
            cur.execute("""
                CREATE TABLE IF NOT EXISTS price_snapshots (
                    time            TIMESTAMPTZ NOT NULL,
                    listing_id      UUID NOT NULL,
                    product_id      UUID NOT NULL,
                    marketplace_id  INTEGER NOT NULL,
                    price           DECIMAL(12,2) NOT NULL,
                    mrp             DECIMAL(12,2),
                    discount_pct    DECIMAL(5,2),
                    in_stock        BOOLEAN,
                    seller_name     VARCHAR(500)
                );
            """)
            cur.execute(
                "SELECT create_hypertable('price_snapshots', 'time', if_not_exists => TRUE);"
            )
            cur.execute("""
                ALTER TABLE price_snapshots SET (
                    timescaledb.compress,
                    timescaledb.compress_segmentby = 'listing_id',
                    timescaledb.compress_orderby = 'time DESC'
                );
            """)
            cur.execute(
                "SELECT add_compression_policy('price_snapshots', INTERVAL '30 days', if_not_exists => TRUE);"
            )
    finally:
        raw_conn.autocommit = was_autocommit


def _create_continuous_aggregate(apps, schema_editor):
    """Create price_daily continuous aggregate + refresh policy.

    TimescaleDB requires these to run outside any transaction block.
    We set autocommit=True on the raw psycopg3 connection, which also
    commits any implicit transaction that psycopg3 may have opened.
    """
    conn = schema_editor.connection
    raw_conn = conn.connection

    was_autocommit = raw_conn.autocommit
    raw_conn.autocommit = True
    try:
        with raw_conn.cursor() as cur:
            cur.execute("""
                CREATE MATERIALIZED VIEW IF NOT EXISTS price_daily
                WITH (timescaledb.continuous) AS
                SELECT
                    time_bucket('1 day', time)  AS day,
                    product_id,
                    marketplace_id,
                    AVG(price)                   AS avg_price,
                    MIN(price)                   AS min_price,
                    MAX(price)                   AS max_price,
                    last(price, time)            AS closing_price,
                    first(price, time)           AS opening_price
                FROM price_snapshots
                GROUP BY day, product_id, marketplace_id;
            """)
            cur.execute("""
                SELECT add_continuous_aggregate_policy('price_daily',
                    start_offset      => INTERVAL '3 days',
                    end_offset        => INTERVAL '1 hour',
                    schedule_interval => INTERVAL '1 hour',
                    if_not_exists     => TRUE);
            """)
    finally:
        raw_conn.autocommit = was_autocommit


class Migration(migrations.Migration):
    # Keep atomic=False as belt-and-suspenders; autocommit is managed per-step.
    atomic = False

    dependencies = [
        ("pricing", "0001_initial"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            _create_price_table_and_hypertable,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            _create_continuous_aggregate,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
