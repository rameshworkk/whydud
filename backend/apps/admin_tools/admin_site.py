"""Custom Django admin site for Whydud platform management."""
from django.contrib.admin import AdminSite


class WhydudAdminSite(AdminSite):
    site_header = "WHYDUD Admin"
    site_title = "WHYDUD Platform"
    index_title = "Platform Management"

    def get_urls(self):
        from django.urls import path

        custom_urls = [
            path(
                "dashboard/",
                self.admin_view(self.dashboard_view),
                name="admin-dashboard",
            ),
            path(
                "system-health/",
                self.admin_view(self.system_health_view),
                name="system-health",
            ),
            path(
                "backfill/",
                self.admin_view(self.backfill_view),
                name="backfill-console",
            ),
            path(
                "enrichment/",
                self.admin_view(self.enrichment_view),
                name="enrichment-console",
            ),
            path(
                "price-intel/",
                self.admin_view(self.price_intel_view),
                name="price-intel",
            ),
            path(
                "analytics/",
                self.admin_view(self.analytics_view),
                name="analytics",
            ),
            path(
                "cluster/",
                self.admin_view(self.cluster_view),
                name="cluster-console",
            ),
            # AJAX endpoints for live updates
            path(
                "api/stats/",
                self.admin_view(self.api_stats),
                name="api-stats",
            ),
            path(
                "api/backfill-status/",
                self.admin_view(self.api_backfill_status),
                name="api-backfill-status",
            ),
        ]
        return custom_urls + super().get_urls()

    # ------------------------------------------------------------------
    # Dashboard home — platform overview
    # ------------------------------------------------------------------

    def dashboard_view(self, request):
        """Platform overview — the admin home page."""
        from datetime import timedelta

        from django.db.models import Count, Q
        from django.shortcuts import render
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product, ProductListing
        from apps.reviews.models import Review

        User = self._get_user_model()
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        context = {
            **self.each_context(request),
            "title": "Platform Dashboard",
            # Product stats
            "product_count": Product.objects.count(),
            "product_lightweight": Product.objects.filter(
                is_lightweight=True
            ).count(),
            "product_enriched": Product.objects.filter(
                is_lightweight=False
            ).count(),
            "product_with_reviews": Product.objects.filter(
                total_reviews__gt=0
            ).count(),
            "product_with_dudscore": Product.objects.exclude(
                dud_score__isnull=True
            ).count(),
            "listing_count": ProductListing.objects.count(),
            # Backfill stats
            "backfill_total": BackfillProduct.objects.count(),
            "backfill_by_status": list(
                BackfillProduct.objects.values("status")
                .annotate(count=Count("id"))
                .order_by("status")
            ),
            "backfill_by_scrape": list(
                BackfillProduct.objects.values("scrape_status")
                .annotate(count=Count("id"))
                .order_by("scrape_status")
            ),
            # Review stats
            "review_count": Review.objects.count(),
            "review_flagged": Review.objects.filter(is_flagged=True).count(),
            # User stats
            "user_count": User.objects.count(),
            "user_new_today": User.objects.filter(
                date_joined__date=today
            ).count(),
            "user_active_7d": User.objects.filter(
                last_login__gte=week_ago
            ).count(),
            # Price snapshots
            "snapshot_count": self._get_snapshot_count(),
            # Marketplace breakdown
            "marketplace_stats": self._get_marketplace_stats(),
        }
        return render(request, "admin/dashboard.html", context)

    # ------------------------------------------------------------------
    # Stub views — implemented in subsequent AD-* prompts
    # ------------------------------------------------------------------

    def system_health_view(self, request):
        """System health dashboard — live service checks + DB/Redis stats."""
        import time

        from django.shortcuts import render

        services = []
        db_stats = {}
        redis_stats = {}
        celery_info = {}
        timescale_stats = {}

        # --- PostgreSQL ---
        services.append(self._check_postgres())

        # --- TimescaleDB ---
        ts_check, timescale_stats = self._check_timescaledb()
        services.append(ts_check)

        # --- Redis ---
        redis_check, redis_stats = self._check_redis()
        services.append(redis_check)

        # --- Meilisearch ---
        services.append(self._check_meilisearch())

        # --- Celery workers ---
        celery_check, celery_info = self._check_celery()
        services.append(celery_check)

        # --- Database stats ---
        db_stats = self._get_db_stats()

        # --- Key table row counts ---
        table_counts = self._get_table_row_counts()

        context = {
            **self.each_context(request),
            "title": "System Health",
            "services": services,
            "db_stats": db_stats,
            "redis_stats": redis_stats,
            "celery_info": celery_info,
            "timescale_stats": timescale_stats,
            "table_counts": table_counts,
        }
        return render(request, "admin/system_health.html", context)

    # ------------------------------------------------------------------
    # Health check helpers (all wrapped in try/except)
    # ------------------------------------------------------------------

    @staticmethod
    def _check_postgres():
        """Check PostgreSQL connectivity with SELECT 1."""
        import time

        from django.db import connection

        try:
            start = time.monotonic()
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
            ms = (time.monotonic() - start) * 1000
            status = "healthy" if ms < 100 else "degraded"
            return {
                "name": "PostgreSQL",
                "status": status,
                "detail": f"{ms:.0f}ms",
            }
        except Exception as e:
            return {"name": "PostgreSQL", "status": "down", "detail": str(e)}

    @staticmethod
    def _check_timescaledb():
        """Check TimescaleDB extension and hypertable info."""
        from django.db import connection

        stats = {}
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT default_version, installed_version "
                    "FROM pg_available_extensions WHERE name = 'timescaledb'"
                )
                row = cur.fetchone()
                if not row or not row[1]:
                    return (
                        {
                            "name": "TimescaleDB",
                            "status": "down",
                            "detail": "Extension not installed",
                        },
                        stats,
                    )
                stats["version"] = row[1]

                # Chunk count
                try:
                    cur.execute(
                        "SELECT count(*) FROM timescaledb_information.chunks"
                    )
                    stats["chunks"] = cur.fetchone()[0]
                except Exception:
                    stats["chunks"] = "N/A"

                # Hypertable info
                try:
                    cur.execute(
                        "SELECT hypertable_name, num_chunks, "
                        "pg_size_pretty(hypertable_size(format('%%I.%%I', hypertable_schema, hypertable_name)::regclass)) "
                        "FROM timescaledb_information.hypertables"
                    )
                    stats["hypertables"] = [
                        {"name": r[0], "chunks": r[1], "size": r[2]}
                        for r in cur.fetchall()
                    ]
                except Exception:
                    stats["hypertables"] = []

                # Continuous aggregates
                try:
                    cur.execute(
                        "SELECT view_name FROM timescaledb_information.continuous_aggregates"
                    )
                    stats["continuous_aggregates"] = [
                        r[0] for r in cur.fetchall()
                    ]
                except Exception:
                    stats["continuous_aggregates"] = []

            return (
                {
                    "name": "TimescaleDB",
                    "status": "healthy",
                    "detail": f"v{stats['version']}, {stats.get('chunks', '?')} chunks",
                },
                stats,
            )
        except Exception as e:
            return (
                {"name": "TimescaleDB", "status": "down", "detail": str(e)},
                stats,
            )

    @staticmethod
    def _check_redis():
        """Check Redis via Django cache set/get round-trip + INFO stats."""
        import time

        stats = {}
        try:
            from django.core.cache import cache

            start = time.monotonic()
            cache.set("_health_check", "ok", 10)
            val = cache.get("_health_check")
            ms = (time.monotonic() - start) * 1000

            if val != "ok":
                return (
                    {
                        "name": "Redis",
                        "status": "degraded",
                        "detail": f"Set/get mismatch ({ms:.0f}ms)",
                    },
                    stats,
                )

            # Get Redis INFO via low-level client
            try:
                client = cache.client.get_client()
                info = client.info()
                stats["used_memory_human"] = info.get(
                    "used_memory_human", "?"
                )
                stats["connected_clients"] = info.get(
                    "connected_clients", "?"
                )
                stats["total_keys"] = sum(
                    info.get(f"db{i}", {}).get("keys", 0) for i in range(16)
                )
                stats["uptime_days"] = info.get("uptime_in_days", "?")
                stats["hit_rate"] = "N/A"
                hits = info.get("keyspace_hits", 0)
                misses = info.get("keyspace_misses", 0)
                if hits + misses > 0:
                    stats["hit_rate"] = f"{hits / (hits + misses) * 100:.1f}%"
            except Exception:
                pass

            status = "healthy" if ms < 50 else "degraded"
            return (
                {
                    "name": "Redis",
                    "status": status,
                    "detail": f"{ms:.0f}ms, {stats.get('used_memory_human', '?')} used",
                },
                stats,
            )
        except Exception as e:
            return (
                {"name": "Redis", "status": "down", "detail": str(e)},
                stats,
            )

    @staticmethod
    def _check_meilisearch():
        """Check Meilisearch /health endpoint."""
        import time
        import urllib.request

        from django.conf import settings

        url = getattr(settings, "MEILISEARCH_URL", "http://localhost:7700")
        try:
            start = time.monotonic()
            req = urllib.request.Request(
                f"{url}/health", method="GET"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                ms = (time.monotonic() - start) * 1000
                status = "healthy" if ms < 500 else "degraded"
                return {
                    "name": "Meilisearch",
                    "status": status,
                    "detail": f"{ms:.0f}ms",
                }
        except Exception as e:
            return {
                "name": "Meilisearch",
                "status": "down",
                "detail": str(e),
            }

    @staticmethod
    def _check_celery():
        """Check Celery workers via inspect.ping + queue info."""
        info = {"workers": [], "queues": {}}
        try:
            from whydud.celery import app

            inspector = app.control.inspect(timeout=5)
            ping = inspector.ping() or {}
            active = inspector.active() or {}
            reserved = inspector.reserved() or {}
            active_queues = inspector.active_queues() or {}
            stats = inspector.stats() or {}

            for worker_name, pong in ping.items():
                worker_active = active.get(worker_name, [])
                worker_reserved = reserved.get(worker_name, [])
                worker_queues = active_queues.get(worker_name, [])
                worker_stats = stats.get(worker_name, {})

                queue_names = [
                    q.get("name", "?") for q in worker_queues
                ]

                # Total tasks completed from stats
                total_tasks = sum(
                    worker_stats.get("total", {}).values()
                ) if isinstance(worker_stats.get("total"), dict) else 0

                info["workers"].append(
                    {
                        "name": worker_name,
                        "status": "online",
                        "active_tasks": len(worker_active),
                        "reserved_tasks": len(worker_reserved),
                        "queues": queue_names,
                        "total_completed": total_tasks,
                    }
                )

            # Aggregate queue depths from reserved tasks
            for worker_name, tasks in reserved.items():
                for task in tasks:
                    q = task.get("delivery_info", {}).get(
                        "routing_key", "default"
                    )
                    info["queues"][q] = info["queues"].get(q, 0) + 1
            # Also count active tasks per queue
            for worker_name, tasks in active.items():
                for task in tasks:
                    q = task.get("delivery_info", {}).get(
                        "routing_key", "default"
                    )
                    info["queues"].setdefault(q, 0)

            worker_count = len(ping)
            if worker_count == 0:
                return (
                    {
                        "name": "Celery Workers",
                        "status": "down",
                        "detail": "No workers responding",
                    },
                    info,
                )
            return (
                {
                    "name": "Celery Workers",
                    "status": "healthy",
                    "detail": f"{worker_count} worker(s) online",
                },
                info,
            )
        except Exception as e:
            return (
                {
                    "name": "Celery Workers",
                    "status": "down",
                    "detail": str(e),
                },
                info,
            )

    @staticmethod
    def _get_db_stats():
        """Get database size and largest tables."""
        from django.db import connection

        stats = {}
        try:
            with connection.cursor() as cur:
                # Total database size
                cur.execute(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                stats["total_size"] = cur.fetchone()[0]

                # Connection pool usage
                cur.execute(
                    "SELECT count(*) FROM pg_stat_activity "
                    "WHERE datname = current_database()"
                )
                stats["active_connections"] = cur.fetchone()[0]

                cur.execute("SHOW max_connections")
                stats["max_connections"] = cur.fetchone()[0]

                # Top 10 largest tables
                cur.execute(
                    "SELECT schemaname || '.' || relname AS table, "
                    "pg_size_pretty(pg_total_relation_size(relid)) AS size, "
                    "pg_total_relation_size(relid) AS raw_size "
                    "FROM pg_catalog.pg_statio_user_tables "
                    "ORDER BY pg_total_relation_size(relid) DESC "
                    "LIMIT 10"
                )
                stats["largest_tables"] = [
                    {"table": r[0], "size": r[1]} for r in cur.fetchall()
                ]
        except Exception:
            pass
        return stats

    @staticmethod
    def _get_table_row_counts():
        """Get row counts for key tables."""
        from django.db import connection

        tables = {
            "products": "products",
            "listings": "product_listings",
            "price_snapshots": "price_snapshots",
            "reviews": "reviews",
            "backfill_products": "backfill_products",
            "users": '"users"."accounts"',
            "search_logs": "search_searchlog",
        }
        counts = {}
        for label, table in tables.items():
            try:
                with connection.cursor() as cur:
                    cur.execute(f"SELECT count(*) FROM {table}")  # noqa: S608
                    counts[label] = cur.fetchone()[0]
            except Exception:
                counts[label] = "error"
        return counts

    def backfill_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Backfill Pipeline"},
        )

    def enrichment_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Enrichment Queue"},
        )

    def price_intel_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Price Intelligence"},
        )

    def analytics_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Analytics"},
        )

    def cluster_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Worker Cluster"},
        )

    # ------------------------------------------------------------------
    # AJAX API endpoints
    # ------------------------------------------------------------------

    def api_stats(self, request):
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product
        from apps.reviews.models import Review

        return JsonResponse(
            {
                "products": Product.objects.count(),
                "backfill": BackfillProduct.objects.count(),
                "reviews": Review.objects.count(),
                "snapshots": self._get_snapshot_count(),
            }
        )

    def api_backfill_status(self, request):
        from django.db.models import Count
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct

        by_status = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(count=Count("id"))
            .values_list("scrape_status", "count")
        )
        return JsonResponse(by_status)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_user_model():
        from django.contrib.auth import get_user_model

        return get_user_model()

    @staticmethod
    def _get_snapshot_count():
        from django.db import connection

        try:
            with connection.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM price_snapshots")
                return cur.fetchone()[0]
        except Exception:
            return 0

    @staticmethod
    def _get_marketplace_stats():
        from django.db.models import Count

        from apps.products.models import ProductListing

        return list(
            ProductListing.objects.values("marketplace__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
