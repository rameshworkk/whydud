"""Custom Django admin site for Whydud platform management."""
from django.contrib.admin import AdminSite
from django.utils.timezone import localtime


class WhydudAdminSite(AdminSite):
    site_header = "WHYDUD Admin"
    site_title = "WHYDUD Platform"
    index_title = "Platform Management"

    def each_context(self, request):
        ctx = super().each_context(request)
        ctx['active_page'] = ''
        # Sidebar badges loaded async via /api/sidebar-badges/
        ctx['sidebar_backfill_badge'] = ''
        ctx['sidebar_enrichment_badge'] = ''
        ctx['sidebar_flagged_reviews'] = 0
        return ctx

    @staticmethod
    def _format_count(n):
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}M"
        if n >= 1_000:
            return f"{n / 1_000:.0f}K"
        return str(n) if n > 0 else ''

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
                "analytics/action/<str:action>/",
                self.admin_view(self.analytics_action),
                name="analytics-action",
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
            # Async data-loading endpoints (pages load shell, then fetch stats)
            path(
                "api/sidebar-badges/",
                self.admin_view(self.api_sidebar_badges),
                name="api-sidebar-badges",
            ),
            path(
                "api/dashboard-data/",
                self.admin_view(self.api_dashboard_data),
                name="api-dashboard-data",
            ),
            path(
                "api/backfill-data/",
                self.admin_view(self.api_backfill_data),
                name="api-backfill-data",
            ),
            path(
                "api/backfill-cluster/",
                self.admin_view(self.api_backfill_cluster),
                name="api-backfill-cluster",
            ),
            path(
                "api/enrichment-data/",
                self.admin_view(self.api_enrichment_data),
                name="api-enrichment-data",
            ),
        ]
        return custom_urls + super().get_urls()

    # ------------------------------------------------------------------
    # Dashboard home — platform overview
    # ------------------------------------------------------------------

    def dashboard_view(self, request):
        """Platform overview — page shell only, stats loaded async via JS."""
        from django.shortcuts import render
        from django.utils import timezone

        now = timezone.now()
        local_hour = timezone.localtime(now).hour
        if local_hour < 12:
            greeting = "Good morning"
        elif local_hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"
        full_name = (getattr(request.user, 'name', '') or '').strip()
        user_first_name = (
            full_name.split()[0] if full_name else request.user.email.split("@")[0]
        )

        context = {
            **self.each_context(request),
            "active_page": "dashboard",
            "title": "Platform Dashboard",
            "greeting": greeting,
            "user_first_name": user_first_name,
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
            "active_page": "system_health",
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
        """Backfill pipeline — page shell only, stats loaded async via JS."""
        from django.shortcuts import render

        from apps.pricing.models import BackfillProduct

        backfill_categories = list(
            BackfillProduct.objects
            .exclude(category_name="")
            .values_list("category_name", flat=True)
            .distinct()
            .order_by("category_name")
        )

        context = {
            **self.each_context(request),
            "active_page": "backfill",
            "title": "Backfill Pipeline",
            "backfill_categories": backfill_categories,
            "online_workers": self._get_online_workers(),
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
    def _resolve_target_nodes(post_data, celery_app):
        """Resolve multi-select target_nodes checkboxes to {prefix: full_worker_name} map.

        Returns (resolved_map, error_msg). If no nodes selected, returns ({}, None).
        """
        selected = post_data.getlist("target_nodes")
        if not selected:
            return {}, None

        ping_result = celery_app.control.ping(timeout=3)
        online = {}
        for resp in ping_result:
            for wn in resp:
                online[wn.split("@")[0]] = wn

        resolved = {}
        missing = []
        for prefix in selected:
            if prefix in online:
                resolved[prefix] = online[prefix]
            else:
                missing.append(prefix)

        if missing:
            avail = ", ".join(online.keys()) or "none"
            return None, f"Error: Workers not online: {', '.join(missing)}. Available: {avail}"

        return resolved, None

    @staticmethod
    def _dispatch_to_nodes(task_func, kwargs, action_prefix, nodes_map, celery_app):
        """Dispatch task to specific nodes via temporary queues. Returns list of (node, task_id)."""
        dispatched = []
        for prefix, full_name in nodes_map.items():
            queue_name = f"{action_prefix}-{prefix}"
            celery_app.control.add_consumer(queue_name, destination=[full_name])
            r = task_func.apply_async(kwargs=kwargs, queue=queue_name)
            dispatched.append((prefix, r.id[:8]))
        return dispatched

    @staticmethod
    def _dispatch_backfill_action(action, post_data):
        """Dispatch a backfill action and return a status message."""
        try:
            if action == "discover":
                from apps.pricing.tasks import run_phase1_discover
                from whydud.celery import app as celery_app

                start = int(post_data.get("sitemap_start", 1))
                end = int(post_data.get("sitemap_end", 5))
                filters = post_data.getlist("discover_filters")
                filter_electronics = "electronics" in filters
                max_products_val = post_data.get("max_products", "").strip()
                max_products = int(max_products_val) if max_products_val else None

                task_kwargs = {
                    "sitemap_start": start,
                    "sitemap_end": end,
                    "filter_electronics": filter_electronics,
                    "max_products": max_products,
                }

                nodes_map, err = WhydudAdminSite._resolve_target_nodes(post_data, celery_app)
                if err:
                    return err

                filter_desc = ""
                if filter_electronics:
                    filter_desc += ", electronics-only"
                if max_products:
                    filter_desc += f", max {max_products}"

                if nodes_map:
                    dispatched = WhydudAdminSite._dispatch_to_nodes(
                        run_phase1_discover,
                        task_kwargs,
                        "discover", nodes_map, celery_app,
                    )
                    parts = [f"{n}:{tid}" for n, tid in dispatched]
                    return f"Discovery → {', '.join(n for n, _ in dispatched)} (sitemaps {start}-{end}{filter_desc}). Tasks: {', '.join(parts)}"
                else:
                    result = run_phase1_discover.delay(**task_kwargs)
                    return f"Discovery started (sitemaps {start}-{end}{filter_desc}). Task: {result.id}"

            elif action == "bh-fill":
                from apps.pricing.tasks import run_phase2_buyhatke
                from whydud.celery import app as celery_app

                batch = int(post_data.get("batch_size", 5000))
                workers = int(post_data.get("workers", 2))
                repeat = post_data.get("repeat") == "on"
                delay_val = post_data.get("delay", "").strip()
                delay = float(delay_val) if delay_val else None

                nodes_map, err = WhydudAdminSite._resolve_target_nodes(post_data, celery_app)
                if err:
                    return err

                category_names = post_data.getlist("category_names")

                task_kwargs = {"batch_size": batch, "repeat": repeat}
                if delay is not None:
                    task_kwargs["delay"] = delay
                if category_names:
                    task_kwargs["category_names"] = category_names
                rpt = " repeat=ON" if repeat else ""
                dly = f" delay={delay}s" if delay else ""
                cat = f" categories={','.join(category_names)}" if category_names else ""

                task_ids = []
                if nodes_map:
                    for prefix, full_name in nodes_map.items():
                        queue_name = f"bh-fill-{prefix}"
                        celery_app.control.add_consumer(queue_name, destination=[full_name])
                        for _ in range(workers):
                            r = run_phase2_buyhatke.apply_async(kwargs=task_kwargs, queue=queue_name)
                            task_ids.append(f"{prefix}:{r.id[:8]}")
                    nodes_str = ",".join(nodes_map.keys())
                    return f"BH-Fill → {nodes_str} ({workers}x each, batch {batch}{rpt}{dly}{cat}). Tasks: {', '.join(task_ids)}"
                else:
                    for _ in range(workers):
                        r = run_phase2_buyhatke.delay(**task_kwargs)
                        task_ids.append(r.id[:8])
                    return f"BH-Fill dispatched ({workers} workers, batch {batch}{rpt}{dly}{cat}). Tasks: {', '.join(task_ids)}"

            elif action == "ph-extend":
                from apps.pricing.tasks import run_phase3_extend
                from whydud.celery import app as celery_app

                limit = int(post_data.get("limit", 5000))
                workers = int(post_data.get("workers", 2))
                repeat = post_data.get("repeat") == "on"
                delay_val = post_data.get("delay", "").strip()
                delay = float(delay_val) if delay_val else None

                nodes_map, err = WhydudAdminSite._resolve_target_nodes(post_data, celery_app)
                if err:
                    return err

                category_names = post_data.getlist("category_names")
                include_discovered = post_data.get("include_discovered") == "on"

                task_kwargs = {"limit": limit, "repeat": repeat}
                if delay is not None:
                    task_kwargs["delay"] = delay
                if category_names:
                    task_kwargs["category_names"] = category_names
                if include_discovered:
                    task_kwargs["include_discovered"] = True
                rpt = " repeat=ON" if repeat else ""
                dly = f" delay={delay}s" if delay else ""
                cat = f" categories={','.join(category_names)}" if category_names else ""
                disc = " +discovered" if include_discovered else ""

                task_ids = []
                if nodes_map:
                    for prefix, full_name in nodes_map.items():
                        queue_name = f"ph-extend-{prefix}"
                        celery_app.control.add_consumer(queue_name, destination=[full_name])
                        for _ in range(workers):
                            r = run_phase3_extend.apply_async(kwargs=task_kwargs, queue=queue_name)
                            task_ids.append(f"{prefix}:{r.id[:8]}")
                    nodes_str = ",".join(nodes_map.keys())
                    return f"PH-Extend → {nodes_str} ({workers}x each, limit {limit}{rpt}{dly}{cat}{disc}). Tasks: {', '.join(task_ids)}"
                else:
                    for _ in range(workers):
                        r = run_phase3_extend.delay(**task_kwargs)
                        task_ids.append(r.id[:8])
                    return f"PH-Extend dispatched ({workers} workers, limit {limit}{rpt}{dly}{cat}{disc}). Tasks: {', '.join(task_ids)}"

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

                nodes_map, err = WhydudAdminSite._resolve_target_nodes(post_data, celery_app)
                if err:
                    return err

                if nodes_map:
                    task_ids = []
                    for prefix, full_name in nodes_map.items():
                        queue_name = f"enrich-{prefix}"
                        celery_app.control.add_consumer(queue_name, destination=[full_name])
                        r = celery_app.send_task(
                            "apps.pricing.backfill.enrichment.enrich_batch",
                            kwargs={"batch_size": batch},
                            queue=queue_name,
                        )
                        task_ids.append(f"{prefix}:{r.id[:8]}")
                    nodes_str = ",".join(nodes_map.keys())
                    return f"Enrichment → {nodes_str} ({batch} products each). Tasks: {', '.join(task_ids)}"
                else:
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

            elif action == "revoke":
                from whydud.celery import app as celery_app

                task_id = post_data.get("task_id", "").strip()
                if not task_id:
                    return "Error: No task ID provided."
                celery_app.control.revoke(task_id, terminate=True, signal="SIGTERM")
                return f"Revoke signal sent to task {task_id[:12]}… (SIGTERM)"

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
        """Enrichment queue — page shell only, stats loaded async via JS."""
        from django.shortcuts import render

        context = {
            **self.each_context(request),
            "active_page": "enrichment",
            "title": "Enrichment Queue",
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
            "active_page": "price_intel",
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
        """Analytics / BI dashboard + Search console (AD-11)."""
        import json
        from datetime import timedelta

        from django.conf import settings
        from django.db import connection
        from django.db.models import Count, Q
        from django.db.models.functions import TruncDate
        from django.shortcuts import render
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct, PriceSnapshot
        from apps.products.models import Product, ProductListing
        from apps.reviews.models import Review

        User = self._get_user_model()
        now = timezone.now()
        thirty_days_ago = now - timedelta(days=30)

        # ---- GROWTH METRICS (30-day daily counts) ----
        products_daily = list(
            Product.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(
                total=Count("id"),
                lightweight=Count("id", filter=Q(is_lightweight=True)),
                enriched=Count("id", filter=Q(is_lightweight=False)),
            )
            .order_by("day")
        )

        users_daily = list(
            User.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        reviews_daily = list(
            Review.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        # Snapshots per day via raw SQL (TimescaleDB hypertable)
        snapshots_daily = []
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT DATE(time) AS day, COUNT(*)
                    FROM price_snapshots
                    WHERE time >= %s
                    GROUP BY DATE(time)
                    ORDER BY day
                """, [thirty_days_ago])
                snapshots_daily = [
                    {"day": row[0].isoformat(), "count": row[1]}
                    for row in cur.fetchall()
                ]
        except Exception:
            pass

        # Format for Chart.js
        products_chart = {
            "labels": [d["day"].isoformat() for d in products_daily],
            "total": [d["total"] for d in products_daily],
            "lightweight": [d["lightweight"] for d in products_daily],
            "enriched": [d["enriched"] for d in products_daily],
        }
        users_chart = {
            "labels": [d["day"].isoformat() for d in users_daily],
            "data": [d["count"] for d in users_daily],
        }
        reviews_chart = {
            "labels": [d["day"].isoformat() for d in reviews_daily],
            "data": [d["count"] for d in reviews_daily],
        }
        snapshots_chart = {
            "labels": [d["day"] for d in snapshots_daily],
            "data": [d["count"] for d in snapshots_daily],
        }

        # ---- MARKETPLACE DISTRIBUTION ----
        products_by_mp = list(
            ProductListing.objects
            .values("marketplace__name")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        mp_dist = {
            "labels": [m["marketplace__name"] for m in products_by_mp],
            "data": [m["count"] for m in products_by_mp],
        }

        # ---- ENRICHMENT FUNNEL ----
        bf_total = BackfillProduct.objects.count()
        bf_bh_filled = BackfillProduct.objects.filter(
            status__in=["bh_filled", "ph_extending", "ph_extended", "done"]
        ).count()
        bf_ph_extended = BackfillProduct.objects.filter(
            status__in=["ph_extended", "done"]
        ).count()
        lightweight_count = Product.objects.filter(is_lightweight=True).count()
        enriched_count = Product.objects.filter(is_lightweight=False).count()
        with_reviews = Product.objects.filter(total_reviews__gt=0).count()
        with_dudscore = Product.objects.filter(dud_score__isnull=False).count()

        funnel = {
            "labels": [
                "Discovered", "BH Filled", "PH Extended",
                "Lightweight", "Enriched", "With Reviews", "With DudScore",
            ],
            "data": [
                bf_total, bf_bh_filled, bf_ph_extended,
                lightweight_count, enriched_count, with_reviews, with_dudscore,
            ],
        }

        # ---- TOP CONTENT ----
        top_by_reviews = list(
            Product.objects
            .filter(total_reviews__gt=0)
            .order_by("-total_reviews")
            .values("title", "total_reviews")[:10]
        )

        top_by_snapshots = []
        try:
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT p.title, COUNT(ps.*) AS cnt
                    FROM price_snapshots ps
                    JOIN products p ON p.id = ps.product_id
                    GROUP BY p.id, p.title
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                top_by_snapshots = [
                    {"title": row[0], "count": row[1]}
                    for row in cur.fetchall()
                ]
        except Exception:
            pass

        top_categories = list(
            Product.objects
            .filter(category__isnull=False)
            .values("category__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )
        top_brands = list(
            Product.objects
            .filter(brand__isnull=False)
            .values("brand__name")
            .annotate(count=Count("id"))
            .order_by("-count")[:10]
        )

        # ---- BACKFILL VELOCITY ----
        discovered_daily = list(
            BackfillProduct.objects
            .filter(created_at__gte=thirty_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        enriched_daily = list(
            BackfillProduct.objects
            .filter(
                scrape_status="scraped",
                updated_at__gte=thirty_days_ago,
            )
            .annotate(day=TruncDate("updated_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        # Estimated days to complete enrichment
        pending_enrichment = BackfillProduct.objects.filter(
            scrape_status="pending"
        ).count()
        recent_enriched = sum(d["count"] for d in enriched_daily)
        avg_daily_rate = recent_enriched / 30 if recent_enriched else 0
        est_days = (
            round(pending_enrichment / avg_daily_rate)
            if avg_daily_rate > 0
            else None
        )

        velocity_chart = {
            "labels": sorted(set(
                [d["day"].isoformat() for d in discovered_daily]
                + [d["day"].isoformat() for d in enriched_daily]
            )),
            "discovered": {
                d["day"].isoformat(): d["count"] for d in discovered_daily
            },
            "enriched": {
                d["day"].isoformat(): d["count"] for d in enriched_daily
            },
        }

        # ---- MEILISEARCH HEALTH ----
        meili_health = {"status": "unknown"}
        meili_stats = {}
        try:
            import httpx

            meili_url = getattr(settings, "MEILISEARCH_URL", "http://localhost:7700")
            meili_key = getattr(settings, "MEILISEARCH_MASTER_KEY", "")
            headers = {"Authorization": f"Bearer {meili_key}"} if meili_key else {}

            resp = httpx.get(f"{meili_url}/health", headers=headers, timeout=5)
            meili_health = resp.json() if resp.status_code == 200 else {"status": "unhealthy"}

            resp = httpx.get(f"{meili_url}/indexes/products/stats", headers=headers, timeout=5)
            if resp.status_code == 200:
                meili_stats = resp.json()
        except Exception as exc:
            meili_health = {"status": "error", "error": str(exc)}

        context = {
            **self.each_context(request),
            "active_page": "analytics",
            "title": "Analytics & BI Dashboard",
            # Growth charts
            "products_chart": json.dumps(products_chart),
            "users_chart": json.dumps(users_chart),
            "reviews_chart": json.dumps(reviews_chart),
            "snapshots_chart": json.dumps(snapshots_chart),
            # Marketplace distribution
            "mp_dist": json.dumps(mp_dist),
            # Enrichment funnel
            "funnel": json.dumps(funnel),
            # Top content
            "top_by_reviews": top_by_reviews,
            "top_by_snapshots": top_by_snapshots,
            "top_categories": top_categories,
            "top_brands": top_brands,
            # Backfill velocity
            "velocity_chart": json.dumps(velocity_chart),
            "pending_enrichment": pending_enrichment,
            "avg_daily_rate": round(avg_daily_rate, 1),
            "est_days": est_days,
            # Meilisearch
            "meili_health": meili_health,
            "meili_stats": meili_stats,
        }
        return render(request, "admin/analytics.html", context)

    def analytics_action(self, request, action):
        """Handle search console actions (reindex, selective sync)."""
        from django.contrib import messages
        from django.shortcuts import redirect

        if request.method != "POST":
            return redirect("admin:analytics")

        try:
            if action == "full-reindex":
                from apps.search.tasks import full_reindex

                result = full_reindex.delay()
                messages.success(
                    request,
                    f"Full Meilisearch reindex queued. Task: {result.id}",
                )

            elif action == "selective-sync":
                from apps.search.tasks import sync_products_to_meilisearch

                result = sync_products_to_meilisearch.delay()
                messages.success(
                    request,
                    f"Selective Meilisearch sync queued. Task: {result.id}",
                )

            else:
                messages.error(request, f"Unknown action: {action}")

        except ImportError as e:
            messages.warning(request, f"Task not available: {e}")
        except Exception as e:
            messages.error(request, f"Failed: {e}")

        return redirect("admin:analytics")

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
            "active_page": "cluster",
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
                    import time as _time

                    time_start = task.get("time_start")
                    if time_start:
                        elapsed = _time.time() - time_start
                        if elapsed < 60:
                            runtime_display = f"{elapsed:.0f}s"
                        elif elapsed < 3600:
                            runtime_display = f"{elapsed / 60:.1f}m"
                        else:
                            runtime_display = f"{elapsed / 3600:.1f}h"
                    else:
                        runtime_display = "—"

                    active_tasks.append({
                        "worker": worker_name,
                        "name": task.get("name", "?").split(".")[-1],
                        "full_name": task.get("name", "?"),
                        "id": task.get("id", "?")[:12],
                        "full_id": task.get("id", "?"),
                        "runtime": round(task.get("time_start", 0) or 0, 1),
                        "runtime_display": runtime_display,
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

    @staticmethod
    def _get_online_workers():
        """Quick ping to discover online Celery workers for node targeting dropdown."""
        try:
            from whydud.celery import app

            ping_result = app.control.ping(timeout=3)
            workers = []
            seen = set()
            for resp in ping_result:
                for worker_name in resp:
                    prefix = worker_name.split("@")[0]
                    if prefix not in seen:
                        seen.add(prefix)
                        workers.append({"prefix": prefix, "full_name": worker_name})
            return sorted(workers, key=lambda w: w["prefix"])
        except Exception:
            return []

    @staticmethod
    def _get_recent_backfill_tasks(limit=20):
        """Query django-celery-results for recent backfill task history."""
        try:
            from django_celery_results.models import TaskResult

            backfill_task_names = [
                "apps.pricing.tasks.run_phase1_discover",
                "apps.pricing.tasks.run_phase2_buyhatke",
                "apps.pricing.tasks.run_phase3_extend",
                "apps.pricing.tasks.run_phase4_inject",
                "apps.pricing.tasks.refresh_price_daily_aggregate",
                "apps.pricing.tasks.scrape_backfill_products_task",
                "apps.pricing.backfill.enrichment.enrich_batch",
            ]

            results = list(
                TaskResult.objects.filter(task_name__in=backfill_task_names)
                .order_by("-date_done")
                .values(
                    "task_id", "task_name", "status", "result",
                    "date_done", "date_created", "worker", "traceback",
                )[:limit]
            )

            for r in results:
                r["short_name"] = (
                    r["task_name"].split(".")[-1] if r["task_name"] else "?"
                )
                r["date_done_str"] = (
                    localtime(r["date_done"]).strftime("%Y-%m-%d %H:%M:%S")
                    if r["date_done"]
                    else "—"
                )
                r["result_short"] = (r["result"] or "")[:120]
                r["traceback_short"] = (r["traceback"] or "")[:200]

            return results
        except Exception:
            return []

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

    def api_sidebar_badges(self, request):
        """Lightweight endpoint for sidebar badge counts."""
        from django.http import JsonResponse

        result = {"backfill": "", "enrichment": "", "flagged_reviews": 0}
        try:
            from apps.pricing.models import BackfillProduct
            pending = BackfillProduct.objects.filter(scrape_status='pending').count()
            result["backfill"] = self._format_count(pending)
            enrichment = BackfillProduct.objects.filter(
                scrape_status='pending', enrichment_priority__lte=2).count()
            result["enrichment"] = self._format_count(enrichment)
        except Exception:
            pass
        try:
            from apps.reviews.models import Review
            result["flagged_reviews"] = Review.objects.filter(is_flagged=True).count()
        except Exception:
            pass
        return JsonResponse(result)

    def api_dashboard_data(self, request):
        """All dashboard stats as JSON — fetched async after page shell loads."""
        import json
        from datetime import timedelta

        from django.db.models import Count
        from django.http import JsonResponse
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product, ProductListing
        from apps.reviews.models import Review

        User = self._get_user_model()
        now = timezone.now()
        today = now.date()
        week_ago = now - timedelta(days=7)

        backfill_by_status = list(
            BackfillProduct.objects.values("status")
            .annotate(count=Count("id"))
            .order_by("status")
        )
        backfill_by_scrape = list(
            BackfillProduct.objects.values("scrape_status")
            .annotate(count=Count("id"))
            .order_by("scrape_status")
        )

        sparkline_data = self._compute_sparkline_data(now, Product, Review, User)

        marketplace_stats = self._get_marketplace_stats()
        # Convert marketplace__name key for JSON safety
        mp_list = [{"name": m.get("marketplace__name", "?"), "count": m["count"]}
                   for m in marketplace_stats]

        return JsonResponse({
            "product_count": Product.objects.count(),
            "product_lightweight": Product.objects.filter(is_lightweight=True).count(),
            "product_enriched": Product.objects.filter(is_lightweight=False).count(),
            "product_with_reviews": Product.objects.filter(total_reviews__gt=0).count(),
            "product_with_dudscore": Product.objects.exclude(dud_score__isnull=True).count(),
            "listing_count": ProductListing.objects.count(),
            "backfill_total": BackfillProduct.objects.count(),
            "backfill_by_status": backfill_by_status,
            "backfill_by_scrape": backfill_by_scrape,
            "review_count": Review.objects.count(),
            "review_flagged": Review.objects.filter(is_flagged=True).count(),
            "user_count": User.objects.count(),
            "user_new_today": User.objects.filter(created_at__date=today).count(),
            "user_active_7d": User.objects.filter(last_login__gte=week_ago).count(),
            "snapshot_count": self._get_snapshot_count(),
            "marketplace_stats": mp_list,
            "sparkline": sparkline_data,
        })

    def api_backfill_data(self, request):
        """Fast backfill stats — DB queries only, no Celery inspector calls."""
        from django.db.models import Count
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct

        total = BackfillProduct.objects.count()

        by_status = dict(
            BackfillProduct.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        by_scrape = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(c=Count("id"))
            .values_list("scrape_status", "c")
        )
        by_priority = dict(
            BackfillProduct.objects.values_list("enrichment_priority")
            .annotate(c=Count("id"))
            .values_list("enrichment_priority", "c")
        )
        by_method = dict(
            BackfillProduct.objects.values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )
        by_review = dict(
            BackfillProduct.objects.values_list("review_status")
            .annotate(c=Count("id"))
            .values_list("review_status", "c")
        )
        by_marketplace = list(
            BackfillProduct.objects.values("marketplace_slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        snapshots_by_source = self._get_snapshots_by_source()

        p1_pending = BackfillProduct.objects.filter(
            scrape_status="pending", enrichment_priority=1
        ).count()
        p2p3_pending = BackfillProduct.objects.filter(
            scrape_status="pending", enrichment_priority__in=[2, 3]
        ).count()
        reviews_pending = BackfillProduct.objects.filter(
            review_status="pending"
        ).count()

        est_p1_hrs = round(p1_pending * 30 / 3600, 1)
        est_p2p3_hrs = round(p2p3_pending * 2 / 3600, 1)
        est_reviews_hrs = round(reviews_pending * 15 / 3600, 1)

        status_labels = [
            "discovered", "bh_filling", "bh_filled",
            "ph_extending", "ph_extended", "done", "failed", "skipped",
        ]
        scrape_labels = ["pending", "enriching", "scraped", "failed"]

        # Proxy configuration for display
        from urllib.parse import urlparse

        from apps.pricing.backfill.config import BackfillConfig

        raw_proxy_url = BackfillConfig.proxy_url()
        masked_proxy_url = ""
        if raw_proxy_url:
            try:
                parsed = urlparse(raw_proxy_url)
                if parsed.username:
                    masked_proxy_url = f"{parsed.scheme}://{parsed.username}:****@{parsed.hostname}"
                    if parsed.port:
                        masked_proxy_url += f":{parsed.port}"
                else:
                    masked_proxy_url = raw_proxy_url
            except Exception:
                masked_proxy_url = "(configured)"

        proxy_config = {
            "enabled": bool(raw_proxy_url),
            "url": masked_proxy_url,
            "retry_interval_mins": round(BackfillConfig.proxy_retry_interval() / 60, 1),
            "burn_threshold": BackfillConfig.proxy_burn_threshold(),
        }

        return JsonResponse({
            "total": total,
            "by_status": by_status,
            "by_scrape": by_scrape,
            "by_priority": {str(k): v for k, v in by_priority.items()},
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
            "proxy_config": proxy_config,
            "status_chart": {
                "labels": [s.replace("_", " ").title() for s in status_labels],
                "data": [by_status.get(s, 0) for s in status_labels],
            },
            "priority_chart": {
                "labels": ["P0 On-demand", "P1 Playwright", "P2 curl_cffi", "P3 curl_cffi-low"],
                "data": [by_priority.get(0, 0), by_priority.get(1, 0),
                         by_priority.get(2, 0), by_priority.get(3, 0)],
            },
            "snapshot_chart": {
                "labels": [s["source"] for s in snapshots_by_source],
                "data": [s["count"] for s in snapshots_by_source],
            },
            "scrape_chart": {
                "labels": [s.title() for s in scrape_labels],
                "data": [by_scrape.get(s, 0) for s in scrape_labels],
            },
        })

    def api_backfill_cluster(self, request):
        """Slow backfill data — Celery inspector, task history, failed products."""
        from django.db.models import Q
        from django.http import JsonResponse

        from apps.pricing.models import BackfillProduct

        _, _, active_tasks = self._get_cluster_data()
        recent_task_results = self._get_recent_backfill_tasks(limit=20)

        failed_products = list(
            BackfillProduct.objects.filter(
                Q(status="failed") | Q(scrape_status="failed")
            )
            .order_by("-updated_at")
            .values(
                "id", "external_id", "marketplace_slug", "error_message",
                "retry_count", "status", "scrape_status", "updated_at",
            )[:50]
        )
        for fp in failed_products:
            fp["updated_at"] = localtime(fp["updated_at"]).strftime("%Y-%m-%d %H:%M")
            fp["id"] = str(fp["id"])

        return JsonResponse({
            "active_tasks": active_tasks,
            "recent_task_results": recent_task_results,
            "failed_products": failed_products,
        })

    def api_enrichment_data(self, request):
        """All enrichment console stats as JSON — fetched async after page shell loads."""
        from datetime import timedelta

        from django.db.models import Count
        from django.http import JsonResponse
        from django.utils import timezone

        from apps.pricing.models import BackfillProduct

        now = timezone.now()
        day_ago = now - timedelta(hours=24)

        total = BackfillProduct.objects.count()

        by_scrape = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(c=Count("id"))
            .values_list("scrape_status", "c")
        )

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

        enriching_qs = BackfillProduct.objects.filter(scrape_status="enriching")
        enriching_total = enriching_qs.count()
        enriching_by_method = dict(
            enriching_qs.values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )

        completed_by_method = dict(
            BackfillProduct.objects.filter(scrape_status="scraped")
            .values_list("enrichment_method")
            .annotate(c=Count("id"))
            .values_list("enrichment_method", "c")
        )

        failed_retryable = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__lt=3
        ).count()
        failed_exhausted = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__gte=3
        ).count()

        enriched_24h = BackfillProduct.objects.filter(
            scrape_status="scraped", updated_at__gte=day_ago
        ).count()

        by_review = dict(
            BackfillProduct.objects.values_list("review_status")
            .annotate(c=Count("id"))
            .values_list("review_status", "c")
        )

        pending_by_marketplace = list(
            BackfillProduct.objects.filter(scrape_status="pending")
            .values("marketplace_slug")
            .annotate(count=Count("id"))
            .order_by("-count")
        )

        est_p0_hrs = round(p0_queue * 30 / 3600, 1)
        est_p1_hrs = round(p1_queue * 30 / 3600, 1)
        est_p2p3_hrs = round((p2_queue + p3_queue) * 2 / 3600, 1)

        bw_p1_gb = round(p1_queue * 625 / (1024 * 1024), 2)
        bw_p2p3_gb = round((p2_queue + p3_queue) * 85 / (1024 * 1024), 2)
        bw_total_gb = round(bw_p1_gb + bw_p2p3_gb, 2)

        stale_threshold = now - timedelta(hours=2)
        stale_products = list(
            BackfillProduct.objects.filter(
                scrape_status="enriching",
                enrichment_queued_at__lt=stale_threshold,
            )
            .order_by("-enrichment_queued_at")
            .values(
                "id", "external_id", "marketplace_slug", "enrichment_method",
                "error_message", "retry_count", "enrichment_queued_at", "updated_at",
            )[:50]
        )
        for sp in stale_products:
            sp["id"] = str(sp["id"])
            if sp["enrichment_queued_at"]:
                sp["enrichment_queued_at"] = localtime(sp["enrichment_queued_at"]).strftime("%Y-%m-%d %H:%M")
            sp["updated_at"] = localtime(sp["updated_at"]).strftime("%Y-%m-%d %H:%M")

        recent_failures = list(
            BackfillProduct.objects.filter(scrape_status="failed")
            .order_by("-updated_at")
            .values(
                "id", "external_id", "marketplace_slug", "enrichment_method",
                "error_message", "retry_count", "updated_at",
            )[:50]
        )
        for rf in recent_failures:
            rf["id"] = str(rf["id"])
            rf["updated_at"] = localtime(rf["updated_at"]).strftime("%Y-%m-%d %H:%M")

        return JsonResponse({
            "total": total,
            "by_scrape": by_scrape,
            "p0_queue": p0_queue,
            "p1_queue": p1_queue,
            "p2_queue": p2_queue,
            "p3_queue": p3_queue,
            "total_queue": p0_queue + p1_queue + p2_queue + p3_queue,
            "enriching_total": enriching_total,
            "enriching_by_method": enriching_by_method,
            "completed_by_method": completed_by_method,
            "completed_total": by_scrape.get("scraped", 0),
            "failed_total": by_scrape.get("failed", 0),
            "failed_retryable": failed_retryable,
            "failed_exhausted": failed_exhausted,
            "enriched_24h": enriched_24h,
            "by_review": by_review,
            "pending_by_marketplace": pending_by_marketplace,
            "est_p0_hrs": est_p0_hrs,
            "est_p1_hrs": est_p1_hrs,
            "est_p2p3_hrs": est_p2p3_hrs,
            "bw_p1_gb": bw_p1_gb,
            "bw_p2p3_gb": bw_p2p3_gb,
            "bw_total_gb": bw_total_gb,
            "stale_products": stale_products,
            "recent_failures": recent_failures,
            "queue_chart": {
                "labels": ["P0 On-demand", "P1 Playwright", "P2 curl_cffi", "P3 curl_cffi-low"],
                "data": [p0_queue, p1_queue, p2_queue, p3_queue],
            },
            "method_chart": {
                "labels": list(completed_by_method.keys()),
                "data": list(completed_by_method.values()),
            },
            "review_chart": {
                "labels": ["Skip", "Pending", "Scraping", "Scraped", "Failed"],
                "data": [
                    by_review.get("skip", 0), by_review.get("pending", 0),
                    by_review.get("scraping", 0), by_review.get("scraped", 0),
                    by_review.get("failed", 0),
                ],
            },
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_sparkline_data(now, Product, Review, User):
        """Compute 7-day daily counts for dashboard sparklines."""
        from datetime import timedelta

        from django.db import connection
        from django.db.models import Count
        from django.db.models.functions import TruncDate

        seven_days_ago = now - timedelta(days=7)

        # Products created per day (last 7 days)
        products_qs = dict(
            Product.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .values_list("day", "count")
        )

        # Reviews created per day
        reviews_qs = dict(
            Review.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .values_list("day", "count")
        )

        # Users created per day
        users_qs = dict(
            User.objects.filter(created_at__gte=seven_days_ago)
            .annotate(day=TruncDate("created_at"))
            .values("day")
            .annotate(count=Count("id"))
            .values_list("day", "count")
        )

        # Price snapshots per day (raw SQL — hypertable)
        snapshots_by_day = {}
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT time::date AS day, COUNT(*) "
                    "FROM price_snapshots "
                    "WHERE time >= %s "
                    "GROUP BY day ORDER BY day",
                    [seven_days_ago],
                )
                for row in cur.fetchall():
                    snapshots_by_day[row[0]] = row[1]
        except Exception:
            pass

        # Build arrays for each day in the 7-day window
        days = [
            (now - timedelta(days=i)).date() for i in range(6, -1, -1)
        ]
        return {
            "labels": [d.strftime("%a") for d in days],
            "products": [products_qs.get(d, 0) for d in days],
            "reviews": [reviews_qs.get(d, 0) for d in days],
            "users": [users_qs.get(d, 0) for d in days],
            "snapshots": [snapshots_by_day.get(d, 0) for d in days],
        }

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
