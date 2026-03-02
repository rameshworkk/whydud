"""Create scoring.dudscore_history as a TimescaleDB hypertable.

DudScoreHistory is managed=False in Django, so we create the table manually.

NOTE: create_hypertable cannot run inside any transaction block (even implicit
ones created by psycopg3).  We use RunPython + raw connection autocommit.
"""
from django.db import migrations


def _create_dudscore_history_hypertable(apps, schema_editor):
    conn = schema_editor.connection
    raw_conn = conn.connection  # underlying psycopg3 connection

    was_autocommit = raw_conn.autocommit
    raw_conn.autocommit = True
    try:
        with raw_conn.cursor() as cur:
            # Ensure TimescaleDB extension exists (idempotent).
            cur.execute("CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;")
            cur.execute("""
                CREATE TABLE IF NOT EXISTS scoring.dudscore_history (
                    time             TIMESTAMPTZ NOT NULL,
                    product_id       UUID NOT NULL,
                    score            DECIMAL(5,2) NOT NULL,
                    config_version   INTEGER NOT NULL,
                    component_scores JSONB NOT NULL
                );
            """)
            cur.execute(
                "SELECT create_hypertable('scoring.dudscore_history', 'time', if_not_exists => TRUE);"
            )
    finally:
        raw_conn.autocommit = was_autocommit


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ("scoring", "0001_initial"),
        ("products", "0001_initial"),
        ("accounts", "0001_initial"),  # ensures scoring schema exists
    ]

    operations = [
        migrations.RunPython(
            _create_dudscore_history_hypertable,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
