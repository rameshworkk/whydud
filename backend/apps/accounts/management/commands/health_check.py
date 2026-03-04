"""System health check command.

Checks PostgreSQL, Redis, Meilisearch, Celery, scraper recency, disk usage,
and backup freshness. Prints a status line per check and exits with code 1
if any critical check fails.

Usage:
    python manage.py health_check
    python manage.py health_check --json    # machine-readable output
"""

import json as json_lib
import os
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Run system health checks across all Whydud infrastructure."

    def add_arguments(self, parser):
        parser.add_argument(
            "--json",
            action="store_true",
            help="Output results as JSON instead of human-readable text.",
        )

    def handle(self, *args, **options):
        output_json = options["json"]
        results: list[dict] = []
        any_critical = False

        # ── 1. PostgreSQL ────────────────────────────────────────────────
        result = self._check_postgres()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 2. Redis ─────────────────────────────────────────────────────
        result = self._check_redis()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 3. Meilisearch ───────────────────────────────────────────────
        result = self._check_meilisearch()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 4. Celery workers ────────────────────────────────────────────
        result = self._check_celery()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 5. Last scrape per marketplace ───────────────────────────────
        result = self._check_scraper_recency()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 6. Disk usage ────────────────────────────────────────────────
        result = self._check_disk_usage()
        results.append(result)
        if result["status"] == "fail":
            any_critical = True

        # ── 7. Last backup ───────────────────────────────────────────────
        result = self._check_last_backup()
        results.append(result)
        # Backup is a warning, not critical
        if result["status"] == "fail":
            any_critical = True

        # ── Output ───────────────────────────────────────────────────────
        if output_json:
            self.stdout.write(json_lib.dumps(
                {"checks": results, "healthy": not any_critical},
                indent=2,
                default=str,
            ))
        else:
            self.stdout.write("\n=== Whydud System Health Check ===\n")
            for r in results:
                icon = "\u2705" if r["status"] == "pass" else ("\u26a0\ufe0f" if r["status"] == "warn" else "\u274c")
                self.stdout.write(f"  {icon} {r['name']}: {r['message']}")
                if r.get("details"):
                    for key, val in r["details"].items():
                        self.stdout.write(f"      {key}: {val}")
            self.stdout.write("")

            if any_critical:
                self.stderr.write(self.style.ERROR("\nHEALTH CHECK FAILED — critical issues detected\n"))
            else:
                self.stdout.write(self.style.SUCCESS("\nAll checks passed.\n"))

        if any_critical:
            raise SystemExit(1)

    # ── Individual checks ────────────────────────────────────────────────

    def _check_postgres(self) -> dict:
        """PostgreSQL connectivity + table counts."""
        name = "PostgreSQL"
        try:
            with connection.cursor() as cursor:
                # Connectivity test
                cursor.execute("SELECT 1")

                # Table counts across all schemas
                table_queries = {
                    "products": "SELECT COUNT(*) FROM products",
                    "product_listings": "SELECT COUNT(*) FROM product_listings",
                    "marketplaces": "SELECT COUNT(*) FROM marketplaces",
                    "categories": "SELECT COUNT(*) FROM categories",
                    "reviews": "SELECT COUNT(*) FROM reviews",
                    "users": 'SELECT COUNT(*) FROM users."accounts"',
                    "whydud_emails": 'SELECT COUNT(*) FROM users."whydud_emails"',
                    "wishlists": 'SELECT COUNT(*) FROM users."wishlists"',
                    "deals": "SELECT COUNT(*) FROM deals",
                    "price_snapshots": "SELECT COUNT(*) FROM price_snapshots",
                    "dudscore_history": 'SELECT COUNT(*) FROM scoring."dudscore_history"',
                    "scraper_jobs": "SELECT COUNT(*) FROM scraper_jobs",
                    "discussions": 'SELECT COUNT(*) FROM community."discussion_threads"',
                    "tco_models": 'SELECT COUNT(*) FROM tco."models"',
                    "reward_balances": 'SELECT COUNT(*) FROM users."reward_balances"',
                    "inbox_emails": 'SELECT COUNT(*) FROM email_intel."inbox_emails"',
                    "sellers": "SELECT COUNT(*) FROM sellers",
                }

                details = {}
                for label, query in table_queries.items():
                    try:
                        cursor.execute(query)
                        count = cursor.fetchone()[0]
                        details[label] = count
                    except Exception:
                        details[label] = "N/A"

                # DB size
                cursor.execute(
                    "SELECT pg_size_pretty(pg_database_size(current_database()))"
                )
                details["db_size"] = cursor.fetchone()[0]

            return {
                "name": name,
                "status": "pass",
                "message": f"Connected — {details.get('db_size', '?')}",
                "details": details,
            }
        except Exception as e:
            return {"name": name, "status": "fail", "message": f"Connection failed: {e}"}

    def _check_redis(self) -> dict:
        """Redis connectivity + memory usage."""
        name = "Redis"
        try:
            from django.conf import settings
            import redis

            redis_url = getattr(settings, "CELERY_BROKER_URL", None) or os.environ.get(
                "REDIS_URL", "redis://localhost:6379/0"
            )
            r = redis.from_url(redis_url, socket_timeout=5)
            info = r.info("memory")

            used = info.get("used_memory_human", "?")
            peak = info.get("used_memory_peak_human", "?")
            maxmem = info.get("maxmemory_human", "?")

            # Key counts
            db_info = r.info("keyspace")
            total_keys = sum(v.get("keys", 0) for v in db_info.values() if isinstance(v, dict))

            return {
                "name": name,
                "status": "pass",
                "message": f"Connected — {used} used / {maxmem} max",
                "details": {
                    "used_memory": used,
                    "peak_memory": peak,
                    "max_memory": maxmem,
                    "total_keys": total_keys,
                },
            }
        except Exception as e:
            return {"name": name, "status": "fail", "message": f"Connection failed: {e}"}

    def _check_meilisearch(self) -> dict:
        """Meilisearch health + document count."""
        name = "Meilisearch"
        try:
            import httpx

            meili_url = os.environ.get("MEILISEARCH_URL", "http://localhost:7700")
            meili_key = os.environ.get("MEILISEARCH_MASTER_KEY", "")

            headers = {}
            if meili_key:
                headers["Authorization"] = f"Bearer {meili_key}"

            # Health check
            resp = httpx.get(f"{meili_url}/health", headers=headers, timeout=5.0)
            if resp.status_code != 200:
                return {"name": name, "status": "fail", "message": f"Health endpoint returned {resp.status_code}"}

            # Get indexes and document counts
            resp_indexes = httpx.get(f"{meili_url}/indexes", headers=headers, timeout=5.0)
            details = {}
            total_docs = 0
            if resp_indexes.status_code == 200:
                data = resp_indexes.json()
                indexes = data.get("results", data) if isinstance(data, dict) else data
                for idx in indexes:
                    idx_name = idx.get("uid", "unknown")
                    doc_count = idx.get("numberOfDocuments", 0)
                    details[f"index:{idx_name}"] = doc_count
                    total_docs += doc_count

            return {
                "name": name,
                "status": "pass",
                "message": f"Healthy — {total_docs} documents across {len(details)} indexes",
                "details": details,
            }
        except Exception as e:
            return {"name": name, "status": "fail", "message": f"Unreachable: {e}"}

    def _check_celery(self) -> dict:
        """Celery worker count via inspect."""
        name = "Celery Workers"
        try:
            from whydud.celery import app

            inspector = app.control.inspect(timeout=5.0)
            active = inspector.active()

            if active is None:
                return {"name": name, "status": "fail", "message": "No workers responding"}

            worker_count = len(active)
            total_tasks = sum(len(tasks) for tasks in active.values())

            details = {}
            for worker_name, tasks in active.items():
                details[worker_name] = f"{len(tasks)} active task(s)"

            # Also check registered queues
            active_queues = inspector.active_queues()
            if active_queues:
                queues_set = set()
                for worker_queues in active_queues.values():
                    for q in worker_queues:
                        queues_set.add(q.get("name", "?"))
                details["queues"] = ", ".join(sorted(queues_set))

            return {
                "name": name,
                "status": "pass",
                "message": f"{worker_count} worker(s), {total_tasks} active task(s)",
                "details": details,
            }
        except Exception as e:
            return {"name": name, "status": "fail", "message": f"Inspect failed: {e}"}

    def _check_scraper_recency(self) -> dict:
        """Last completed scrape per marketplace (should be < 48h ago)."""
        name = "Scraper Recency"
        try:
            from apps.scraping.models import ScraperJob
            from apps.products.models import Marketplace

            threshold = datetime.now(timezone.utc) - timedelta(hours=48)
            marketplaces = Marketplace.objects.values_list("slug", flat=True)

            details = {}
            stale_count = 0

            for slug in marketplaces:
                last_job = (
                    ScraperJob.objects.filter(
                        marketplace__slug=slug,
                        status__in=["completed", "partial"],
                    )
                    .order_by("-finished_at")
                    .values("finished_at", "items_scraped")
                    .first()
                )

                if last_job and last_job["finished_at"]:
                    age = datetime.now(timezone.utc) - last_job["finished_at"]
                    hours_ago = int(age.total_seconds() / 3600)
                    items = last_job["items_scraped"]
                    status_icon = "\u2705" if last_job["finished_at"] > threshold else "\u26a0\ufe0f"
                    details[slug] = f"{status_icon} {hours_ago}h ago ({items} items)"
                    if last_job["finished_at"] < threshold:
                        stale_count += 1
                else:
                    details[slug] = "\u274c Never scraped"
                    stale_count += 1

            total = len(list(marketplaces))
            fresh = total - stale_count

            status = "pass" if stale_count == 0 else ("warn" if stale_count < total else "fail")
            return {
                "name": name,
                "status": status,
                "message": f"{fresh}/{total} marketplaces scraped within 48h",
                "details": details,
            }
        except Exception as e:
            return {"name": name, "status": "warn", "message": f"Could not check: {e}"}

    def _check_disk_usage(self) -> dict:
        """Disk usage — warn at 80%, critical at 90%."""
        name = "Disk Usage"
        try:
            usage = shutil.disk_usage("/")
            percent = (usage.used / usage.total) * 100
            total_gb = usage.total / (1024**3)
            free_gb = usage.free / (1024**3)

            if percent >= 90:
                status = "fail"
            elif percent >= 80:
                status = "warn"
            else:
                status = "pass"

            return {
                "name": name,
                "status": status,
                "message": f"{percent:.1f}% used ({free_gb:.1f} GB free of {total_gb:.1f} GB)",
                "details": {
                    "total_gb": f"{total_gb:.1f}",
                    "used_gb": f"{(usage.used / (1024**3)):.1f}",
                    "free_gb": f"{free_gb:.1f}",
                    "percent_used": f"{percent:.1f}%",
                },
            }
        except Exception as e:
            return {"name": name, "status": "warn", "message": f"Could not check: {e}"}

    def _check_last_backup(self) -> dict:
        """Last backup time — should be < 12h ago."""
        name = "Last Backup"
        try:
            backup_dir = os.environ.get("BACKUP_DIR", "/backups")
            ts_file = Path(backup_dir) / ".last_backup_time"

            if not ts_file.exists():
                # Also check for any .dump.gz files
                backup_path = Path(backup_dir)
                if backup_path.exists():
                    dumps = sorted(backup_path.glob("whydud_*.dump.gz"))
                    if dumps:
                        last_modified = datetime.fromtimestamp(
                            dumps[-1].stat().st_mtime, tz=timezone.utc
                        )
                        age = datetime.now(timezone.utc) - last_modified
                        hours = int(age.total_seconds() / 3600)
                        status = "pass" if hours < 12 else ("warn" if hours < 24 else "fail")
                        return {
                            "name": name,
                            "status": status,
                            "message": f"Last backup {hours}h ago (from file mtime)",
                            "details": {
                                "file": str(dumps[-1].name),
                                "hours_ago": hours,
                            },
                        }

                return {
                    "name": name,
                    "status": "warn",
                    "message": "No backup timestamp found — backups may not be configured",
                }

            timestamp_str = ts_file.read_text().strip()
            # Parse YYYYMMDD_HHMMSS format
            backup_time = datetime.strptime(timestamp_str, "%Y%m%d_%H%M%S").replace(
                tzinfo=timezone.utc
            )
            age = datetime.now(timezone.utc) - backup_time
            hours = int(age.total_seconds() / 3600)

            if hours < 12:
                status = "pass"
            elif hours < 24:
                status = "warn"
            else:
                status = "fail"

            return {
                "name": name,
                "status": status,
                "message": f"Last backup {hours}h ago",
                "details": {
                    "timestamp": timestamp_str,
                    "hours_ago": hours,
                },
            }
        except Exception as e:
            return {"name": name, "status": "warn", "message": f"Could not check: {e}"}
