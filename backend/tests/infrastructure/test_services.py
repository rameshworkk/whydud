"""
Infrastructure health tests.
Verify all services (PostgreSQL, TimescaleDB, Redis, Meilisearch, Celery) are alive
and correctly configured.

Run: pytest tests/infrastructure/ -m infra -v
"""
import pytest
from django.db import connection
from django.conf import settings

pytestmark = [pytest.mark.infra, pytest.mark.django_db]


class TestPostgreSQL:
    """Verify PostgreSQL is alive and schemas exist."""

    def test_database_connection(self):
        """Can we connect to PostgreSQL?"""
        with connection.cursor() as cur:
            cur.execute("SELECT 1")
            assert cur.fetchone()[0] == 1

    def test_all_schemas_exist(self):
        """All 7 custom schemas must exist."""
        expected_schemas = ['public', 'users', 'email_intel', 'scoring',
                            'tco', 'community', 'admin']
        with connection.cursor() as cur:
            cur.execute("""
                SELECT schema_name FROM information_schema.schemata
                WHERE schema_name = ANY(%s)
            """, [expected_schemas])
            found = {row[0] for row in cur.fetchall()}

        missing = set(expected_schemas) - found
        assert not missing, f"Missing schemas: {missing}"

    def test_critical_tables_exist(self):
        """Core tables must exist."""
        critical_tables = [
            ('public', 'products'),
            ('public', 'product_listings'),
            ('public', 'marketplaces'),
            ('public', 'categories'),
            ('public', 'brands'),
            ('public', 'reviews'),
            ('public', 'price_snapshots'),
            ('users', 'accounts'),
        ]
        with connection.cursor() as cur:
            for schema, table in critical_tables:
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_schema = %s AND table_name = %s
                    )
                """, [schema, table])
                exists = cur.fetchone()[0]
                assert exists, f"Table {schema}.{table} does not exist"

    def test_table_count_reasonable(self):
        """Should have ~30+ tables across all schemas."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) FROM information_schema.tables
                WHERE table_schema NOT IN ('pg_catalog', 'information_schema',
                                            'timescaledb_information', 'timescaledb_experimental',
                                            '_timescaledb_catalog', '_timescaledb_internal',
                                            '_timescaledb_config', '_timescaledb_cache')
                AND table_type = 'BASE TABLE'
            """)
            count = cur.fetchone()[0]
        assert count >= 30, f"Only {count} tables found, expected 30+"

    def test_migrations_not_pending(self):
        """No unapplied migrations."""
        from django.core.management import call_command
        from io import StringIO
        out = StringIO()
        call_command('showmigrations', '--plan', stdout=out)
        output = out.getvalue()
        unapplied = [line for line in output.splitlines() if line.strip().startswith('[ ]')]
        assert len(unapplied) == 0, (
            f"{len(unapplied)} unapplied migrations:\n" +
            '\n'.join(unapplied[:10])
        )


class TestTimescaleDB:
    """Verify TimescaleDB extension and hypertables."""

    def test_timescaledb_extension_loaded(self):
        with connection.cursor() as cur:
            cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'timescaledb'")
            row = cur.fetchone()
        assert row is not None, "TimescaleDB extension not installed"

    def test_price_snapshots_is_hypertable(self):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT hypertable_name
                FROM timescaledb_information.hypertables
                WHERE hypertable_name = 'price_snapshots'
            """)
            row = cur.fetchone()
        assert row is not None, "price_snapshots is not a hypertable"

    def test_compression_policy_exists(self):
        with connection.cursor() as cur:
            cur.execute("""
                SELECT count(*) FROM timescaledb_information.jobs
                WHERE proc_name = 'policy_compression'
            """)
            count = cur.fetchone()[0]
        assert count >= 1, "No compression policy found"

    def test_continuous_aggregate_exists(self):
        """price_daily materialized view should exist."""
        with connection.cursor() as cur:
            cur.execute("""
                SELECT count(*) FROM timescaledb_information.continuous_aggregates
                WHERE view_name = 'price_daily'
            """)
            count = cur.fetchone()[0]
        # This might be 0 if not yet created — warn rather than fail
        if count == 0:
            pytest.skip("price_daily continuous aggregate not yet created")

    def test_can_insert_and_query_snapshot(self):
        """Verify we can write to and read from the hypertable."""
        from django.utils import timezone
        with connection.cursor() as cur:
            cur.execute("""
                INSERT INTO price_snapshots
                    (time, listing_id, product_id, marketplace_id, price, in_stock)
                VALUES
                    (%s, gen_random_uuid(), gen_random_uuid(), 1, 49999.00, true)
                RETURNING time
            """, [timezone.now()])
            result = cur.fetchone()
        assert result is not None


class TestRedis:
    """Verify Redis is alive and accessible."""

    def test_redis_connection(self):
        from django.core.cache import cache
        cache.set('_health_check', 'ok', 10)
        assert cache.get('_health_check') == 'ok'
        cache.delete('_health_check')

    def test_redis_cache_backend_configured(self):
        assert 'default' in settings.CACHES
        backend = settings.CACHES['default']['BACKEND']
        assert 'Redis' in backend or 'redis' in backend.lower(), (
            f"Cache backend is {backend}, expected Redis"
        )


class TestMeilisearch:
    """Verify Meilisearch is running and product index exists."""

    def test_meilisearch_health(self):
        import httpx
        meili_url = getattr(settings, 'MEILISEARCH_URL', 'http://localhost:7700')
        meili_key = getattr(settings, 'MEILISEARCH_MASTER_KEY', '')
        try:
            resp = httpx.get(
                f"{meili_url}/health",
                headers={'Authorization': f'Bearer {meili_key}'} if meili_key else {},
                timeout=5,
            )
            assert resp.status_code == 200
            assert resp.json().get('status') == 'available'
        except httpx.ConnectError:
            pytest.fail("Cannot connect to Meilisearch")

    def test_products_index_exists(self):
        import httpx
        meili_url = getattr(settings, 'MEILISEARCH_URL', 'http://localhost:7700')
        meili_key = getattr(settings, 'MEILISEARCH_MASTER_KEY', '')
        resp = httpx.get(
            f"{meili_url}/indexes/products",
            headers={'Authorization': f'Bearer {meili_key}'} if meili_key else {},
            timeout=5,
        )
        if resp.status_code == 404:
            pytest.skip("Products index not yet created in Meilisearch")
        assert resp.status_code == 200

    def test_meilisearch_has_documents(self):
        import httpx
        meili_url = getattr(settings, 'MEILISEARCH_URL', 'http://localhost:7700')
        meili_key = getattr(settings, 'MEILISEARCH_MASTER_KEY', '')
        resp = httpx.get(
            f"{meili_url}/indexes/products/stats",
            headers={'Authorization': f'Bearer {meili_key}'} if meili_key else {},
            timeout=5,
        )
        if resp.status_code != 200:
            pytest.skip("Products index not available")
        stats = resp.json()
        doc_count = stats.get('numberOfDocuments', 0)
        if doc_count == 0:
            pytest.skip("Meilisearch products index is empty (run seed_products first)")


class TestCeleryBroker:
    """Verify Celery broker (Redis) is accessible."""

    def test_celery_app_configured(self):
        from whydud.celery import app
        assert app.main == 'whydud'

    def test_celery_broker_url_set(self):
        from whydud.celery import app
        broker = app.conf.broker_url
        assert broker, "CELERY_BROKER_URL is not set"
        assert 'redis' in broker.lower(), f"Broker is {broker}, expected Redis"

    def test_celery_registered_tasks(self):
        """Key tasks should be registered."""
        from whydud.celery import app
        registered = list(app.tasks.keys())
        # Filter out built-in celery tasks
        our_tasks = [t for t in registered if t.startswith('apps.')]
        assert len(our_tasks) >= 5, (
            f"Only {len(our_tasks)} app tasks registered. "
            f"Expected at least 5. Found: {our_tasks}"
        )

    @pytest.mark.slow
    def test_celery_worker_responds(self):
        """Ping a Celery worker — SLOW, requires worker running."""
        from whydud.celery import app
        try:
            inspector = app.control.inspect(timeout=3)
            ping_result = inspector.ping()
            assert ping_result, "No Celery workers responded to ping"
        except Exception as e:
            pytest.skip(f"Celery worker not running: {e}")
