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
                "backfill/action/<str:action>/",
                self.admin_view(self.backfill_action),
                name="backfill-action",
            ),
            path(
                "enrichment/",
                self.admin_view(self.enrichment_view),
                name="enrichment-console",
            ),
            path(
                "enrichment/action/<str:action>/",
                self.admin_view(self.enrichment_action),
                name="enrichment-action",
            ),
            path(
                "price-intel/",
                self.admin_view(self.price_intel_view),
                name="price-intel",
            ),
            path(
                "price-intel/action/<str:action>/",
                self.admin_view(self.price_intel_action),
                name="price-intel-action",
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

    # ------------------------------------------------------------------
    # Backfill Pipeline Console (AD-3)
    # ------------------------------------------------------------------

    def backfill_view(self, request):
        """Backfill pipeline management — stats, charts, action buttons."""
        import json

        from django.db.models import Count, Q
        from django.shortcuts import render

        from apps.pricing.models import BackfillProduct

        total = BackfillProduct.objects.count()

        # --- By status ---
        by_status = dict(
            BackfillProduct.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )

        # --- By scrape_status ---
        by_scrape = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(c=Count("id"))
            .values_list("scrape_status", "c")
        )

        # --- By enrichment_priority ---
        by_priority = dict(
            BackfillProduct.objects.values_list("enrichment_priority")
            .annotate(c=Count("id"))
            .values_list("enrichment_priority", "c")
        )

        # --- By enrichment_method ---
        by_method = dict(
            BackfillProduct.objects.values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )

        # --- By review_status ---
        by_review = dict(
            BackfillProduct.objects.values_list("review_status")
            .annotate(c=Count("id"))
            .values_list("review_status", "c")
        )

        # --- By marketplace ---
        by_marketplace = list(
            BackfillProduct.objects.values("marketplace_slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # --- Price snapshots by source ---
        snapshots_by_source = self._get_snapshots_by_source()

        # --- Estimated time remaining ---
        p1_pending = BackfillProduct.objects.filter(
            scrape_status="pending", enrichment_priority=1
        ).count()
        p2p3_pending = BackfillProduct.objects.filter(
            scrape_status="pending", enrichment_priority__in=[2, 3]
        ).count()
        reviews_pending = BackfillProduct.objects.filter(
            review_status="pending"
        ).count()

        # P1: ~30s/product, P2/P3: ~2s/product, reviews: ~15s/product
        est_p1_hrs = round(p1_pending * 30 / 3600, 1)
        est_p2p3_hrs = round(p2p3_pending * 2 / 3600, 1)
        est_reviews_hrs = round(reviews_pending * 15 / 3600, 1)

        # --- Failed products (last 50) ---
        failed_products = list(
            BackfillProduct.objects.filter(
                Q(status="failed") | Q(scrape_status="failed")
            )
            .order_by("-updated_at")
            .values(
                "id",
                "external_id",
                "marketplace_slug",
                "error_message",
                "retry_count",
                "status",
                "scrape_status",
                "updated_at",
            )[:50]
        )
        # Serialize updated_at for template
        for fp in failed_products:
            fp["updated_at"] = fp["updated_at"].strftime("%Y-%m-%d %H:%M")

        # --- Chart data as JSON ---
        status_labels = [
            "discovered", "bh_filling", "bh_filled",
            "ph_extending", "ph_extended", "done", "failed", "skipped",
        ]
        status_chart = json.dumps({
            "labels": [s.replace("_", " ").title() for s in status_labels],
            "data": [by_status.get(s, 0) for s in status_labels],
        })

        priority_chart = json.dumps({
            "labels": ["P0 On-demand", "P1 Playwright", "P2 curl_cffi", "P3 curl_cffi-low"],
            "data": [
                by_priority.get(0, 0),
                by_priority.get(1, 0),
                by_priority.get(2, 0),
                by_priority.get(3, 0),
            ],
        })

        snapshot_chart = json.dumps({
            "labels": [s["source"] for s in snapshots_by_source],
            "data": [s["count"] for s in snapshots_by_source],
        })

        scrape_labels = ["pending", "enriching", "scraped", "failed"]
        scrape_chart = json.dumps({
            "labels": [s.title() for s in scrape_labels],
            "data": [by_scrape.get(s, 0) for s in scrape_labels],
        })

        context = {
            **self.each_context(request),
            "title": "Backfill Pipeline",
            "total": total,
            "by_status": by_status,
            "by_scrape": by_scrape,
            "by_priority": by_priority,
            "by_method": by_method,
            "by_review": by_review,
            "by_marketplace": by_marketplace,
            "snapshots_by_source": snapshots_by_source,
            "p1_pending": p1_pending,
            "p2p3_pending": p2p3_pending,
            "reviews_pending": reviews_pending,
            "est_p1_hrs": est_p1_hrs,
            "est_p2p3_hrs": est_p2p3_hrs,
            "est_reviews_hrs": est_reviews_hrs,
            "failed_products": failed_products,
            "status_chart": status_chart,
            "priority_chart": priority_chart,
            "snapshot_chart": snapshot_chart,
            "scrape_chart": scrape_chart,
        }
        return render(request, "admin/backfill_console.html", context)

    def backfill_action(self, request, action):
        """Handle POST actions from the backfill console."""
        from django.contrib import messages
        from django.shortcuts import redirect

        if request.method != "POST":
            messages.error(request, "Actions require POST.")
            return redirect("admin:backfill-console")

        result_msg = self._dispatch_backfill_action(action, request.POST)
        if result_msg.startswith("Error"):
            messages.error(request, result_msg)
        else:
            messages.success(request, result_msg)

        return redirect("admin:backfill-console")

    @staticmethod
    def _dispatch_backfill_action(action, post_data):
        """Dispatch a backfill action and return a status message."""
        try:
            if action == "discover":
                from apps.pricing.tasks import run_phase1_discover

                start = int(post_data.get("sitemap_start", 1))
                end = int(post_data.get("sitemap_end", 5))
                result = run_phase1_discover.delay(
                    sitemap_start=start, sitemap_end=end
                )
                return f"Discovery started (sitemaps {start}-{end}). Task: {result.id}"

            elif action == "bh-fill":
                from apps.pricing.tasks import run_phase2_buyhatke

                batch = int(post_data.get("batch_size", 5000))
                workers = int(post_data.get("workers", 2))
                task_ids = []
                for _ in range(workers):
                    r = run_phase2_buyhatke.delay(batch_size=batch)
                    task_ids.append(r.id[:8])
                return f"BH-Fill dispatched ({workers} workers, batch {batch}). Tasks: {', '.join(task_ids)}"

            elif action == "ph-extend":
                from apps.pricing.tasks import run_phase3_extend

                limit = int(post_data.get("limit", 5000))
                workers = int(post_data.get("workers", 2))
                task_ids = []
                for _ in range(workers):
                    r = run_phase3_extend.delay(limit=limit)
                    task_ids.append(r.id[:8])
                return f"PH-Extend dispatched ({workers} workers, limit {limit}). Tasks: {', '.join(task_ids)}"

            elif action == "create-lightweight":
                from apps.pricing.backfill.lightweight_creator import (
                    create_lightweight_records,
                )

                batch = int(post_data.get("batch_size", 2000))
                result = create_lightweight_records(batch_size=batch)
                created = result.get("created", 0)
                return f"Created {created} lightweight products (batch {batch})."

            elif action == "assign-priorities":
                from apps.pricing.backfill.prioritizer import (
                    assign_enrichment_priorities,
                    assign_review_targets,
                    populate_derived_fields,
                )

                d = populate_derived_fields()
                p = assign_enrichment_priorities()
                r = assign_review_targets()
                return (
                    f"Priorities assigned. Derived: {d}, "
                    f"P1: {p.get('p1', 0)}, P2: {p.get('p2', 0)}, "
                    f"Reviews: {r} targets"
                )

            elif action == "enrich":
                from whydud.celery import app as celery_app

                batch = int(post_data.get("batch_size", 100))
                result = celery_app.send_task(
                    "apps.pricing.backfill.enrichment.enrich_batch",
                    kwargs={"batch_size": batch},
                )
                return f"Enrichment batch queued ({batch} products). Task: {result.id}"

            elif action == "run-overnight":
                from django.core.management import call_command
                import threading

                # Run overnight in a background thread so we don't block the response
                def _run():
                    call_command("backfill_prices", "run-overnight")

                t = threading.Thread(target=_run, daemon=True)
                t.start()
                return "Overnight run started in background thread."

            elif action == "refresh-aggregate":
                from apps.pricing.tasks import refresh_price_daily_aggregate

                result = refresh_price_daily_aggregate.delay()
                return f"Aggregate refresh queued. Task: {result.id}"

            elif action == "reset-failed":
                from apps.pricing.models import BackfillProduct

                which = post_data.get("which", "all")
                if which == "scrape":
                    count = BackfillProduct.objects.filter(
                        scrape_status="failed"
                    ).update(scrape_status="pending", retry_count=0, error_message="")
                    return f"Reset {count} failed enrichments to pending."
                elif which == "review":
                    count = BackfillProduct.objects.filter(
                        review_status="failed"
                    ).update(review_status="pending", error_message="")
                    return f"Reset {count} failed reviews to pending."
                else:
                    count = BackfillProduct.objects.filter(
                        status="failed"
                    ).update(status="discovered", retry_count=0, error_message="")
                    return f"Reset {count} failed BackfillProducts to discovered."

            elif action == "retry-failed":
                from apps.pricing.models import BackfillProduct

                count = BackfillProduct.objects.filter(
                    scrape_status="failed", retry_count__lt=3
                ).update(scrape_status="pending", error_message="")
                return f"Retried {count} failed enrichments (retry_count < 3)."

            else:
                return f"Error: Unknown action '{action}'."

        except Exception as e:
            return f"Error: {e}"

    @staticmethod
    def _get_snapshots_by_source():
        """Get price snapshot counts grouped by source."""
        from django.db import connection

        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT source, COUNT(*) FROM price_snapshots "
                    "GROUP BY source ORDER BY count DESC"
                )
                return [{"source": r[0], "count": r[1]} for r in cur.fetchall()]
        except Exception:
            return []

    # ------------------------------------------------------------------
    # Enrichment Management Console (AD-5)
    # ------------------------------------------------------------------

    def enrichment_view(self, request):
        """Enrichment queue management — priority breakdown, throughput, bandwidth."""
        import json
        from datetime import timedelta

        from django.db.models import Count, Q
        from django.shortcuts import render
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct

        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        total = BackfillProduct.objects.count()

        # --- By scrape_status ---
        by_scrape = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(c=Count("id"))
            .values_list("scrape_status", "c")
        )

        # --- Queue depth by enrichment_priority (pending only) ---
        queue_by_priority = dict(
            BackfillProduct.objects.filter(scrape_status="pending")
            .values_list("enrichment_priority")
            .annotate(c=Count("id"))
            .values_list("enrichment_priority", "c")
        )
        p0_queue = queue_by_priority.get(0, 0)
        p1_queue = queue_by_priority.get(1, 0)
        p2_queue = queue_by_priority.get(2, 0)
        p3_queue = queue_by_priority.get(3, 0)

        # --- Currently enriching by method ---
        enriching_qs = BackfillProduct.objects.filter(scrape_status="enriching")
        enriching_total = enriching_qs.count()
        enriching_by_method = dict(
            enriching_qs.values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )

        # --- Completed by method ---
        completed_by_method = dict(
            BackfillProduct.objects.filter(scrape_status="scraped")
            .values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )

        # --- Failed breakdown ---
        failed_retryable = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__lt=3
        ).count()
        failed_exhausted = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__gte=3
        ).count()

        # --- Throughput: enriched in last 24h ---
        enriched_24h = BackfillProduct.objects.filter(
            scrape_status="scraped", updated_at__gte=day_ago
        ).count()

        # --- Review status ---
        by_review = dict(
            BackfillProduct.objects.values_list("review_status")
            .annotate(c=Count("id"))
            .values_list("review_status", "c")
        )

        # --- By marketplace (pending enrichment only) ---
        pending_by_marketplace = list(
            BackfillProduct.objects.filter(scrape_status="pending")
            .values("marketplace_slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        # --- Estimated time remaining ---
        # P0/P1: ~30s/product (Playwright), P2/P3: ~2s/product (curl_cffi)
        est_p0_hrs = round(p0_queue * 30 / 3600, 1)
        est_p1_hrs = round(p1_queue * 30 / 3600, 1)
        est_p2p3_hrs = round((p2_queue + p3_queue) * 2 / 3600, 1)

        # --- Bandwidth estimates ---
        # P1 Playwright: ~625KB/product, P2/P3 curl_cffi: ~85KB/product
        bw_p1_gb = round(p1_queue * 625 / (1024 * 1024), 2)
        bw_p2p3_gb = round((p2_queue + p3_queue) * 85 / (1024 * 1024), 2)
        bw_total_gb = round(bw_p1_gb + bw_p2p3_gb, 2)

        # --- Stale enrichments (enriching for > 2 hours) ---
        stale_threshold = now - timedelta(hours=2)
        stale_products = list(
            BackfillProduct.objects.filter(
                scrape_status="enriching",
                enrichment_queued_at__lt=stale_threshold,
            )
            .order_by("-enrichment_queued_at")
            .values(
                "id",
                "external_id",
                "marketplace_slug",
                "enrichment_method",
                "error_message",
                "retry_count",
                "enrichment_queued_at",
                "updated_at",
            )[:50]
        )
        for sp in stale_products:
            if sp["enrichment_queued_at"]:
                sp["enrichment_queued_at"] = sp["enrichment_queued_at"].strftime(
                    "%Y-%m-%d %H:%M"
                )
            sp["updated_at"] = sp["updated_at"].strftime("%Y-%m-%d %H:%M")

        # --- Recent failures (last 50) ---
        recent_failures = list(
            BackfillProduct.objects.filter(scrape_status="failed")
            .order_by("-updated_at")
            .values(
                "id",
                "external_id",
                "marketplace_slug",
                "enrichment_method",
                "error_message",
                "retry_count",
                "updated_at",
            )[:50]
        )
        for rf in recent_failures:
            rf["updated_at"] = rf["updated_at"].strftime("%Y-%m-%d %H:%M")

        # --- Chart data ---
        queue_chart = json.dumps(
            {
                "labels": [
                    "P0 On-demand",
                    "P1 Playwright",
                    "P2 curl_cffi",
                    "P3 curl_cffi-low",
                ],
                "data": [p0_queue, p1_queue, p2_queue, p3_queue],
            }
        )

        method_chart = json.dumps(
            {
                "labels": list(completed_by_method.keys()),
                "data": list(completed_by_method.values()),
            }
        )

        review_chart = json.dumps(
            {
                "labels": ["Skip", "Pending", "Scraping", "Scraped", "Failed"],
                "data": [
                    by_review.get("skip", 0),
                    by_review.get("pending", 0),
                    by_review.get("scraping", 0),
                    by_review.get("scraped", 0),
                    by_review.get("failed", 0),
                ],
            }
        )

        context = {
            **self.each_context(request),
            "title": "Enrichment Queue",
            "total": total,
            "by_scrape": by_scrape,
            # Queue depths
            "p0_queue": p0_queue,
            "p1_queue": p1_queue,
            "p2_queue": p2_queue,
            "p3_queue": p3_queue,
            "total_queue": p0_queue + p1_queue + p2_queue + p3_queue,
            # Currently enriching
            "enriching_total": enriching_total,
            "enriching_by_method": enriching_by_method,
            # Completed
            "completed_by_method": completed_by_method,
            "completed_total": by_scrape.get("scraped", 0),
            # Failed
            "failed_total": by_scrape.get("failed", 0),
            "failed_retryable": failed_retryable,
            "failed_exhausted": failed_exhausted,
            # Throughput
            "enriched_24h": enriched_24h,
            # Reviews
            "by_review": by_review,
            # Marketplace
            "pending_by_marketplace": pending_by_marketplace,
            # Time estimates
            "est_p0_hrs": est_p0_hrs,
            "est_p1_hrs": est_p1_hrs,
            "est_p2p3_hrs": est_p2p3_hrs,
            # Bandwidth
            "bw_p1_gb": bw_p1_gb,
            "bw_p2p3_gb": bw_p2p3_gb,
            "bw_total_gb": bw_total_gb,
            # Tables
            "stale_products": stale_products,
            "recent_failures": recent_failures,
            # Charts
            "queue_chart": queue_chart,
            "method_chart": method_chart,
            "review_chart": review_chart,
        }
        return render(request, "admin/enrichment_console.html", context)

    def enrichment_action(self, request, action):
        """Handle POST actions from the enrichment console."""
        from django.contrib import messages
        from django.shortcuts import redirect

        if request.method != "POST":
            messages.error(request, "Actions require POST.")
            return redirect("admin:enrichment-console")

        result_msg = self._dispatch_enrichment_action(action, request.POST)
        if result_msg.startswith("Error"):
            messages.error(request, result_msg)
        else:
            messages.success(request, result_msg)

        return redirect("admin:enrichment-console")

    @staticmethod
    def _dispatch_enrichment_action(action, post_data):
        """Dispatch an enrichment action and return a status message."""
        try:
            if action == "enrich-batch":
                from whydud.celery import app as celery_app

                batch = int(post_data.get("batch_size", 100))
                result = celery_app.send_task(
                    "apps.pricing.backfill.enrichment.enrich_batch",
                    kwargs={"batch_size": batch},
                )
                return f"Enrichment batch queued ({batch} products). Task: {result.id}"

            elif action == "assign-priorities":
                from apps.pricing.backfill.prioritizer import (
                    assign_enrichment_priorities,
                    populate_derived_fields,
                )

                d = populate_derived_fields()
                p = assign_enrichment_priorities()
                return (
                    f"Priorities assigned. Derived: {d}, "
                    f"P1: {p.get('p1', 0)}, P2: {p.get('p2', 0)}"
                )

            elif action == "assign-review-targets":
                from apps.pricing.backfill.prioritizer import assign_review_targets

                max_targets = int(post_data.get("max_targets", 100000))
                count = assign_review_targets(max_review_products=max_targets)
                return f"Marked {count} products for review scraping."

            elif action == "cleanup-stale":
                from whydud.celery import app as celery_app

                result = celery_app.send_task(
                    "apps.pricing.backfill.enrichment.cleanup_stale_enrichments",
                )
                return f"Stale cleanup queued. Task: {result.id}"

            elif action == "reset-failed-enrichments":
                from apps.pricing.models import BackfillProduct

                count = BackfillProduct.objects.filter(
                    scrape_status="failed"
                ).update(scrape_status="pending", retry_count=0, error_message="")
                return f"Reset {count} failed enrichments to pending."

            elif action == "retry-retryable":
                from apps.pricing.models import BackfillProduct

                count = BackfillProduct.objects.filter(
                    scrape_status="failed", retry_count__lt=3
                ).update(scrape_status="pending", error_message="")
                return f"Retried {count} failed enrichments (retry_count < 3)."

            elif action == "reset-failed-reviews":
                from apps.pricing.models import BackfillProduct

                count = BackfillProduct.objects.filter(
                    review_status="failed"
                ).update(review_status="pending", error_message="")
                return f"Reset {count} failed reviews to pending."

            elif action == "check-review-completion":
                from whydud.celery import app as celery_app

                result = celery_app.send_task(
                    "apps.pricing.backfill.enrichment.check_review_completion",
                )
                return f"Review completion check queued. Task: {result.id}"

            else:
                return f"Error: Unknown action '{action}'."

        except Exception as e:
            return f"Error: {e}"

    def price_intel_view(self, request):
        """Price intelligence console — snapshot stats, TimescaleDB health,
        anomaly detection, deal tracking, price alerts."""
        import json
        from datetime import timedelta

        from django.db import connection
        from django.db.models import Avg, Count, F, Q
        from django.shortcuts import render
        from django.utils import timezone

        now = timezone.now()
        today = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        # ---- PRICE SNAPSHOTS ----
        with connection.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM price_snapshots")
            total_snapshots = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM price_snapshots WHERE time >= %s",
                [today],
            )
            snapshots_today = cur.fetchone()[0]

            cur.execute(
                "SELECT source, COUNT(*) FROM price_snapshots GROUP BY source ORDER BY COUNT(*) DESC"
            )
            by_source = [{"source": row[0], "count": row[1]} for row in cur.fetchall()]

        source_labels = json.dumps([s["source"] for s in by_source])
        source_counts = json.dumps([s["count"] for s in by_source])

        # ---- TIMESCALEDB HEALTH ----
        tsdb_health = {}
        try:
            with connection.cursor() as cur:
                # Hypertable info
                cur.execute("""
                    SELECT hypertable_name, num_chunks, compression_enabled
                    FROM timescaledb_information.hypertables
                    WHERE hypertable_name = 'price_snapshots'
                """)
                row = cur.fetchone()
                if row:
                    tsdb_health["hypertable"] = row[0]
                    tsdb_health["num_chunks"] = row[1]
                    tsdb_health["compression_enabled"] = row[2]

                # Chunk count + compressed
                cur.execute("""
                    SELECT
                        COUNT(*) AS total_chunks,
                        COUNT(*) FILTER (WHERE is_compressed) AS compressed_chunks
                    FROM timescaledb_information.chunks
                    WHERE hypertable_name = 'price_snapshots'
                """)
                row = cur.fetchone()
                if row:
                    tsdb_health["total_chunks"] = row[0]
                    tsdb_health["compressed_chunks"] = row[1]

                # Compression ratio (approximate from chunk sizes)
                cur.execute("""
                    SELECT
                        pg_size_pretty(
                            hypertable_size('price_snapshots')
                        )
                """)
                row = cur.fetchone()
                tsdb_health["table_size"] = row[0] if row else "N/A"

                # Check if continuous aggregate exists
                cur.execute("""
                    SELECT materialization_hypertable_name
                    FROM timescaledb_information.continuous_aggregates
                    WHERE view_name = 'price_daily'
                """)
                row = cur.fetchone()
                tsdb_health["has_aggregate"] = row is not None

        except Exception:
            tsdb_health["error"] = True

        # ---- PRICE ANOMALIES (7d) ----
        anomalies = {"drops": [], "spikes": [], "drop_count": 0, "spike_count": 0}
        try:
            with connection.cursor() as cur:
                # Find significant price changes in last 7 days
                # Compare earliest and latest snapshot per listing in the window
                cur.execute("""
                    WITH listing_window AS (
                        SELECT DISTINCT ON (listing_id)
                            listing_id, product_id, price AS old_price, time AS old_time
                        FROM price_snapshots
                        WHERE time >= NOW() - INTERVAL '7 days'
                          AND price > 0
                        ORDER BY listing_id, time ASC
                    ),
                    latest AS (
                        SELECT DISTINCT ON (listing_id)
                            listing_id, price AS new_price, time AS new_time
                        FROM price_snapshots
                        WHERE time >= NOW() - INTERVAL '7 days'
                          AND price > 0
                        ORDER BY listing_id, time DESC
                    )
                    SELECT
                        lw.product_id, lw.listing_id,
                        lw.old_price, lt.new_price,
                        ROUND(((lt.new_price - lw.old_price) / lw.old_price * 100)::numeric, 1) AS change_pct
                    FROM listing_window lw
                    JOIN latest lt ON lw.listing_id = lt.listing_id
                    WHERE lw.old_price > 0
                      AND lw.old_price != lt.new_price
                      AND ABS((lt.new_price - lw.old_price) / lw.old_price) > 0.3
                    ORDER BY change_pct ASC
                    LIMIT 50
                """)
                rows = cur.fetchall()

                # Fetch product titles for context
                product_ids = list({r[0] for r in rows})
                product_titles = {}
                if product_ids:
                    from apps.products.models import Product
                    product_titles = dict(
                        Product.objects.filter(id__in=product_ids)
                        .values_list("id", "title")
                    )

                for row in rows:
                    item = {
                        "product_id": str(row[0]),
                        "product_title": (product_titles.get(row[0], "Unknown"))[:50],
                        "old_price": float(row[2]),
                        "new_price": float(row[3]),
                        "change_pct": float(row[4]),
                    }
                    if item["change_pct"] < -30:
                        anomalies["drops"].append(item)
                    elif item["change_pct"] > 50:
                        anomalies["spikes"].append(item)

                # Sort drops by magnitude (most negative first)
                anomalies["drops"].sort(key=lambda x: x["change_pct"])
                anomalies["spikes"].sort(key=lambda x: x["change_pct"], reverse=True)
                anomalies["drop_count"] = len(anomalies["drops"])
                anomalies["spike_count"] = len(anomalies["spikes"])
                # Keep top 10 each for display
                anomalies["drops"] = anomalies["drops"][:10]
                anomalies["spikes"] = anomalies["spikes"][:10]

        except Exception:
            anomalies["error"] = True

        # ---- PRICE ALERTS ----
        from apps.pricing.models import PriceAlert

        active_alerts = PriceAlert.objects.filter(is_active=True).count()
        triggered_today = PriceAlert.objects.filter(
            is_triggered=True, triggered_at__gte=today,
        ).count()

        # Avg time from creation to trigger
        avg_trigger_time = None
        try:
            triggered = PriceAlert.objects.filter(
                is_triggered=True, triggered_at__isnull=False,
            ).annotate(
                trigger_delta=F("triggered_at") - F("created_at"),
            ).aggregate(avg=Avg("trigger_delta"))
            if triggered["avg"]:
                avg_trigger_time = round(triggered["avg"].total_seconds() / 86400, 1)
        except Exception:
            pass

        # ---- DEAL DETECTION ----
        deal_stats = {}
        try:
            from apps.deals.models import Deal

            active_deals = Deal.objects.filter(is_active=True).count()
            deals_today = Deal.objects.filter(detected_at__gte=today).count()
            by_type = list(
                Deal.objects.filter(is_active=True)
                .values("deal_type")
                .annotate(count=Count("id"))
                .order_by("-count")
            )
            deal_stats = {
                "active": active_deals,
                "today": deals_today,
                "by_type": by_type,
                "type_labels": json.dumps([d["deal_type"] for d in by_type]),
                "type_counts": json.dumps([d["count"] for d in by_type]),
            }
        except Exception:
            deal_stats["error"] = True

        ctx = {
            **self.each_context(request),
            "title": "Price Intelligence",
            # Snapshots
            "total_snapshots": total_snapshots,
            "snapshots_today": snapshots_today,
            "by_source": by_source,
            "source_labels": source_labels,
            "source_counts": source_counts,
            # TimescaleDB
            "tsdb": tsdb_health,
            # Anomalies
            "anomalies": anomalies,
            # Alerts
            "active_alerts": active_alerts,
            "triggered_today": triggered_today,
            "avg_trigger_days": avg_trigger_time,
            # Deals
            "deals": deal_stats,
        }
        return render(request, "admin/price_intel.html", ctx)

    def price_intel_action(self, request, action):
        """Handle POST actions from the price intelligence console."""
        from django.contrib import messages
        from django.shortcuts import redirect

        if request.method != "POST":
            messages.error(request, "Actions require POST.")
            return redirect("admin:price-intel")

        try:
            if action == "refresh-aggregate":
                from apps.pricing.tasks import refresh_price_daily_aggregate

                result = refresh_price_daily_aggregate.delay()
                messages.success(
                    request,
                    f"Aggregate refresh queued. Task: {result.id}",
                )

            elif action == "detect-deals":
                from apps.deals.tasks import detect_blockbuster_deals

                result = detect_blockbuster_deals.delay()
                messages.success(
                    request,
                    f"Deal detection queued. Task: {result.id}",
                )

            else:
                messages.error(request, f"Unknown action: {action}")

        except ImportError as e:
            messages.warning(request, f"Task not available: {e}")
        except Exception as e:
            messages.error(request, f"Failed: {e}")

        return redirect("admin:price-intel")

    def analytics_view(self, request):
        from django.shortcuts import render

        return render(
            request,
            "admin/stub.html",
            {**self.each_context(request), "title": "Analytics"},
        )

    # ------------------------------------------------------------------
    # Worker Cluster Console (AD-4)
    # ------------------------------------------------------------------

    # Known cluster nodes — matches OPERATIONS_GUIDE.md Section 7.1
    CLUSTER_NODES = [
        {
            "id": "primary",
            "label": "PRIMARY",
            "ip": "10.8.0.1",
            "spec": "Contabo 12GB / 6 vCPU",
            "role": "All services + celery-worker",
        },
        {
            "id": "replica",
            "label": "REPLICA",
            "ip": "10.8.0.2",
            "spec": "Contabo 8GB / 4 vCPU",
            "role": "All services + celery-scraping",
        },
        {
            "id": "oci-w1",
            "label": "whyd1 (OCI)",
            "ip": "10.8.0.3",
            "spec": "OCI ARM 1GB + 8GB swap",
            "role": "celery-enrichment only",
        },
        {
            "id": "oci-w2",
            "label": "whyd2 (OCI)",
            "ip": "10.8.0.4",
            "spec": "OCI ARM 1GB + 8GB swap",
            "role": "celery-enrichment only",
        },
    ]

    def cluster_view(self, request):
        """Worker cluster monitoring — per-node status, queues, tasks."""
        import json

        from django.shortcuts import render

        workers, queues, active_tasks = self._get_cluster_data()

        # Build node cards: merge known topology with live data
        online_hostnames = {w["name"] for w in workers}
        nodes = []
        for node_def in self.CLUSTER_NODES:
            # Match by checking if any online worker hostname contains the node id
            matched_worker = None
            for w in workers:
                if node_def["id"] in w["name"].lower():
                    matched_worker = w
                    break

            if matched_worker:
                nodes.append({
                    **node_def,
                    "status": "online",
                    "hostname": matched_worker["name"],
                    "active_tasks": matched_worker["active_tasks"],
                    "reserved_tasks": matched_worker["reserved_tasks"],
                    "queues": matched_worker["queues"],
                    "total_completed": matched_worker["total_completed"],
                    "prefetch_count": matched_worker.get("prefetch_count", "?"),
                    "concurrency": matched_worker.get("concurrency", "?"),
                    "uptime": matched_worker.get("uptime", ""),
                })
            else:
                nodes.append({
                    **node_def,
                    "status": "offline",
                    "hostname": "",
                    "active_tasks": 0,
                    "reserved_tasks": 0,
                    "queues": [],
                    "total_completed": 0,
                    "prefetch_count": "?",
                    "concurrency": "?",
                    "uptime": "",
                })

        # Also add any unknown workers (not in CLUSTER_NODES)
        known_ids = {n["id"] for n in self.CLUSTER_NODES}
        for w in workers:
            name_lower = w["name"].lower()
            if not any(kid in name_lower for kid in known_ids):
                nodes.append({
                    "id": w["name"],
                    "label": w["name"],
                    "ip": "",
                    "spec": "Unknown",
                    "role": "Unknown",
                    "status": "online",
                    "hostname": w["name"],
                    "active_tasks": w["active_tasks"],
                    "reserved_tasks": w["reserved_tasks"],
                    "queues": w["queues"],
                    "total_completed": w["total_completed"],
                    "prefetch_count": w.get("prefetch_count", "?"),
                    "concurrency": w.get("concurrency", "?"),
                    "uptime": w.get("uptime", ""),
                })

        online_count = sum(1 for n in nodes if n["status"] == "online")
        total_active = sum(n["active_tasks"] for n in nodes)
        total_reserved = sum(n["reserved_tasks"] for n in nodes)
        total_completed = sum(n["total_completed"] for n in nodes)

        # Queue depth chart data
        queue_chart = json.dumps({
            "labels": list(queues.keys()) if queues else ["(none)"],
            "data": list(queues.values()) if queues else [0],
        })

        context = {
            **self.each_context(request),
            "title": "Worker Cluster",
            "nodes": nodes,
            "online_count": online_count,
            "total_nodes": len(nodes),
            "total_active": total_active,
            "total_reserved": total_reserved,
            "total_completed": total_completed,
            "queues": queues,
            "queue_chart": queue_chart,
            "active_tasks": active_tasks,
        }
        return render(request, "admin/cluster_console.html", context)

    @staticmethod
    def _get_cluster_data():
        """Fetch live Celery worker data. Returns (workers, queues, active_tasks)."""
        workers = []
        queues = {}
        active_tasks = []
        try:
            from whydud.celery import app

            inspector = app.control.inspect(timeout=5)
            ping = inspector.ping() or {}
            active = inspector.active() or {}
            reserved = inspector.reserved() or {}
            active_queues = inspector.active_queues() or {}
            stats = inspector.stats() or {}

            for worker_name in ping:
                worker_active = active.get(worker_name, [])
                worker_reserved = reserved.get(worker_name, [])
                worker_queues_list = active_queues.get(worker_name, [])
                worker_stats = stats.get(worker_name, {})

                queue_names = [q.get("name", "?") for q in worker_queues_list]

                total_tasks = (
                    sum(worker_stats.get("total", {}).values())
                    if isinstance(worker_stats.get("total"), dict)
                    else 0
                )

                # Uptime from stats
                uptime_secs = worker_stats.get("clock", 0)
                if isinstance(uptime_secs, (int, float)) and uptime_secs > 0:
                    hours = int(uptime_secs // 3600)
                    mins = int((uptime_secs % 3600) // 60)
                    uptime_str = f"{hours}h {mins}m"
                else:
                    uptime_str = ""

                # Prefetch and concurrency
                prefetch = worker_stats.get("prefetch_count", "?")
                pool = worker_stats.get("pool", {})
                concurrency = (
                    pool.get("max-concurrency", "?")
                    if isinstance(pool, dict)
                    else "?"
                )

                workers.append({
                    "name": worker_name,
                    "active_tasks": len(worker_active),
                    "reserved_tasks": len(worker_reserved),
                    "queues": queue_names,
                    "total_completed": total_tasks,
                    "prefetch_count": prefetch,
                    "concurrency": concurrency,
                    "uptime": uptime_str,
                })

                # Collect active task details
                for task in worker_active:
                    active_tasks.append({
                        "worker": worker_name,
                        "name": task.get("name", "?").split(".")[-1],
                        "full_name": task.get("name", "?"),
                        "id": task.get("id", "?")[:12],
                        "runtime": round(task.get("time_start", 0) or 0, 1),
                        "args": str(task.get("args", []))[:80],
                        "kwargs": str(task.get("kwargs", {}))[:80],
                    })

            # Aggregate queue depths
            for worker_name, tasks in reserved.items():
                for task in tasks:
                    q = task.get("delivery_info", {}).get(
                        "routing_key", "default"
                    )
                    queues[q] = queues.get(q, 0) + 1
            for worker_name, tasks in active.items():
                for task in tasks:
                    q = task.get("delivery_info", {}).get(
                        "routing_key", "default"
                    )
                    queues.setdefault(q, 0)

        except Exception:
            pass

        return workers, queues, active_tasks

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
