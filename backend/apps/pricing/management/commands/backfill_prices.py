"""Management command for the multi-phase price history backfill pipeline.

Usage::

    # Phase 0: Backfill existing ProductListings via BuyHatke (instant win)
    python manage.py backfill_prices existing --marketplace amazon-in --limit 500
    python manage.py backfill_prices existing --dry-run

    # Phase 1: Discover products from PH sitemaps
    python manage.py backfill_prices discover --start 1 --end 5
    python manage.py backfill_prices discover --start 1 --end 1 --limit 50 --no-filter

    # Phase 2: BuyHatke bulk fill for discovered products
    python manage.py backfill_prices bh-fill --batch 5000
    python manage.py backfill_prices bh-fill --marketplace amazon-in
    python manage.py backfill_prices bh-fill --celery --workers 4  # dispatch to Celery workers

    # Phase 3: PH deep history extension for top products
    python manage.py backfill_prices ph-extend --limit 5000
    python manage.py backfill_prices ph-extend --celery --workers 4  # dispatch to Celery workers

    # Phase 4a: Targeted scrape of backfill products
    python manage.py backfill_prices scrape --marketplace amazon-in --limit 50
    python manage.py backfill_prices scrape --dry-run
    python manage.py backfill_prices scrape --limit 100 --inject

    # Phase 4b: Inject cached data after spiders create ProductListings
    python manage.py backfill_prices inject --batch 5000
    python manage.py backfill_prices inject --marketplace amazon-in --dry-run

    # Lightweight records: Product+Listing from tracker data (no scraping)
    python manage.py backfill_prices create-lightweight --batch 1000

    # Utilities
    python manage.py backfill_prices status
    python manage.py backfill_prices reset-failed
    python manage.py backfill_prices refresh-aggregate

    # Retry failed (granular)
    python manage.py backfill_prices retry-failed --scrape --dry-run
    python manage.py backfill_prices retry-failed --reviews
    python manage.py backfill_prices retry-failed --history

    # Skip low-value products
    python manage.py backfill_prices skip-products --price-below 10000
    python manage.py backfill_prices skip-products --category "grocery"

    # Overnight enrichment runner
    python manage.py backfill_prices run-overnight --stop-at 06:00

    # Data verification
    python manage.py backfill_prices verify-data
"""
from __future__ import annotations

import asyncio
import sys

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.models import Count


class Command(BaseCommand):
    help = "Multi-phase price history backfill pipeline"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="subcommand")
        sub.required = True

        # ── Phase 0: existing ────────────────────────────────────
        p0 = sub.add_parser("existing", help="Backfill existing ProductListings via BuyHatke")
        p0.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p0.add_argument("--limit", type=int, default=2000, help="Max listings to process")
        p0.add_argument("--delay", type=float, default=None, help="Override BH request delay (seconds)")
        p0.add_argument("--dry-run", action="store_true", help="Fetch data but don't insert")

        # ── Phase 1: discover ────────────────────────────────────
        p1 = sub.add_parser("discover", help="Discover products from PH sitemaps")
        p1.add_argument("--start", type=int, default=1, help="First sitemap index (1-343)")
        p1.add_argument("--end", type=int, default=5, help="Last sitemap index (inclusive)")
        p1.add_argument("--limit", type=int, default=None, help="Max products to process")
        p1.add_argument("--filter-electronics", action="store_true", help="Only keep electronics/tech products (off by default)")
        p1.add_argument("--delay", type=float, default=None, help="Override PH request delay")

        # ── Phase 2: bh-fill ─────────────────────────────────────
        p2 = sub.add_parser("bh-fill", help="BuyHatke bulk price history fill")
        p2.add_argument("--batch", type=int, default=5000, help="Batch size per worker")
        p2.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p2.add_argument("--delay", type=float, default=None, help="Override BH request delay")
        p2.add_argument("--celery", action="store_true", help="Dispatch to Celery workers instead of running in-process")
        p2.add_argument("--workers", type=int, default=4, help="Number of Celery tasks to dispatch (default: 4)")

        # ── Phase 3: ph-extend ───────────────────────────────────
        p3 = sub.add_parser("ph-extend", help="Extend top products with PH deep history")
        p3.add_argument("--limit", type=int, default=5000, help="Max products per worker")
        p3.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p3.add_argument("--delay", type=float, default=None, help="Override PH request delay")
        p3.add_argument("--celery", action="store_true", help="Dispatch to Celery workers instead of running in-process")
        p3.add_argument("--workers", type=int, default=4, help="Number of Celery tasks to dispatch (default: 4)")

        # ── Phase 4a: scrape ─────────────────────────────────────
        ps = sub.add_parser("scrape", help="Targeted scrape of backfill product ASINs/FPIDs")
        ps.add_argument("--batch", type=int, default=None, help="URLs per spider subprocess")
        ps.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        ps.add_argument("--limit", type=int, default=None, help="Max products to scrape")
        ps.add_argument("--dry-run", action="store_true", help="Show candidates without scraping")
        ps.add_argument("--include-retried", action="store_true", help="Include retry_count >= 3")
        ps.add_argument("--inject", action="store_true", help="Run Phase 4 inject after scraping")

        # ── Phase 4b: inject ─────────────────────────────────────
        p4 = sub.add_parser("inject", help="Inject cached price data after spider enrichment")
        p4.add_argument("--batch", type=int, default=5000, help="Batch size")
        p4.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p4.add_argument("--dry-run", action="store_true", help="Find matches but don't inject")

        # ── Lightweight record creator ─────────────────────────────
        plw = sub.add_parser(
            "create-lightweight",
            help="Create Product+Listing from tracker data (no scraping)",
        )
        plw.add_argument("--batch", type=int, default=1000, help="Batch size per loop iteration")

        # ── Priority + review target assignment ────────────────────
        pap = sub.add_parser(
            "assign-priorities",
            help="Assign enrichment priorities (P1/P2/P3) and review targets",
        )
        pap.add_argument(
            "--max-review", type=int, default=100_000,
            help="Max products to mark for review scraping (default: 100000)",
        )

        # ── Enrichment ────────────────────────────────────────────
        pen = sub.add_parser(
            "enrich",
            help="Run tiered enrichment (Playwright for P0-P1, curl_cffi for P2-P3)",
        )
        pen.add_argument(
            "--batch", type=int, default=100,
            help="Number of products per batch (default: 100)",
        )
        pen.add_argument(
            "--id", type=str, default=None, dest="product_id",
            help="Enrich a single BackfillProduct by UUID",
        )

        # ── Utilities ────────────────────────────────────────────
        pst = sub.add_parser("status", help="Show backfill pipeline status dashboard")
        pst.add_argument("--watch", action="store_true", help="Refresh every 30s (Ctrl+C to stop)")
        pst.add_argument("--json", action="store_true", dest="json_output", help="Machine-readable JSON output")
        sub.add_parser("reset-failed", help="Reset failed BackfillProducts for retry")
        sub.add_parser("refresh-aggregate", help="Refresh price_daily continuous aggregate")

        # ── Retry Failed (granular) ──────────────────────────────
        prf = sub.add_parser(
            "retry-failed",
            help="Reset failed enrichments/reviews/history for retry (increments retry_count)",
        )
        prf.add_argument("--scrape", action="store_true", help="Reset failed enrichments to pending")
        prf.add_argument("--reviews", action="store_true", help="Reset failed review scrapes to pending")
        prf.add_argument("--history", action="store_true", help="Reset failed history fetches to Discovered")
        prf.add_argument("--dry-run", action="store_true", help="Show counts without making changes")

        # ── Skip Products ────────────────────────────────────────
        psk = sub.add_parser(
            "skip-products",
            help="Skip low-value products from enrichment pipeline",
        )
        psk.add_argument(
            "--price-below", type=int, default=None,
            help="Skip products with current_price below N paisa (e.g. 10000 = under Rs.100)",
        )
        psk.add_argument(
            "--category", type=str, default=None,
            help="Skip products matching category pattern (case-insensitive regex)",
        )
        psk.add_argument("--dry-run", action="store_true", help="Show counts without making changes")

        # ── Run Overnight ────────────────────────────────────────
        pov = sub.add_parser(
            "run-overnight",
            help="All-in-one overnight enrichment runner",
        )
        pov.add_argument(
            "--stop-at", type=str, default="06:00",
            help="Stop time in HH:MM IST (default: 06:00)",
        )
        pov.add_argument(
            "--batch", type=int, default=100,
            help="Enrichment batch size per iteration (default: 100)",
        )
        pov.add_argument(
            "--progress-interval", type=int, default=300,
            help="Seconds between progress reports (default: 300 = 5 min)",
        )

        # ── Verify Data ──────────────────────────────────────────
        sub.add_parser(
            "verify-data",
            help="Run data quality checks and print warnings",
        )

    def handle(self, *args, **options):
        subcommand = options["subcommand"]
        handler = getattr(self, f"_handle_{subcommand.replace('-', '_')}")
        handler(**options)

    # ── Phase 0 ──────────────────────────────────────────────────

    def _handle_existing(self, **options):
        from apps.pricing.backfill.phase0_existing import backfill_existing_listings

        self.stdout.write(self.style.MIGRATE_HEADING("Phase 0: BuyHatke backfill for existing listings"))
        result = asyncio.run(
            backfill_existing_listings(
                marketplace_slug=options.get("marketplace"),
                limit=options.get("limit", 2000),
                delay=options.get("delay"),
                dry_run=options.get("dry_run", False),
            )
        )
        self._print_result("Phase 0", result)

    # ── Phase 1 ──────────────────────────────────────────────────

    def _handle_discover(self, **options):
        from apps.pricing.backfill.phase1_discover import discover_from_sitemaps

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Phase 1: Discover from PH sitemaps {options['start']}–{options['end']}"
        ))
        result = asyncio.run(
            discover_from_sitemaps(
                sitemap_start=options["start"],
                sitemap_end=options["end"],
                filter_electronics=options.get("filter_electronics", False),
                max_products=options.get("limit"),
                delay=options.get("delay"),
            )
        )
        self._print_result("Phase 1", result)

    # ── Phase 2 ──────────────────────────────────────────────────

    def _handle_bh_fill(self, **options):
        if options.get("celery"):
            return self._dispatch_celery_bh_fill(**options)

        from apps.pricing.backfill.phase2_buyhatke import buyhatke_bulk_fill

        self.stdout.write(self.style.MIGRATE_HEADING("Phase 2: BuyHatke bulk fill"))
        result = asyncio.run(
            buyhatke_bulk_fill(
                batch_size=options.get("batch", 5000),
                marketplace_slug=options.get("marketplace"),
                delay=options.get("delay"),
            )
        )
        self._print_result("Phase 2", result)

    def _dispatch_celery_bh_fill(self, **options):
        from apps.pricing.tasks import run_phase2_buyhatke

        workers = options.get("workers", 4)
        batch = options.get("batch", 5000)
        marketplace = options.get("marketplace")
        delay = options.get("delay")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Phase 2: Dispatching {workers} Celery tasks (batch={batch} each)"
        ))

        task_ids = []
        for i in range(workers):
            result = run_phase2_buyhatke.apply_async(
                kwargs={
                    "batch_size": batch,
                    "marketplace_slug": marketplace,
                    "delay": delay,
                },
            )
            task_ids.append(result.id)
            self.stdout.write(f"  Worker {i + 1}: task_id={result.id}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDispatched {workers} bh-fill tasks to Celery. "
            f"Each claims up to {batch} products via SKIP LOCKED.\n"
            f"Monitor via: celery -A whydud inspect active\n"
            f"Or Flower dashboard."
        ))

    # ── Phase 3 ──────────────────────────────────────────────────

    def _handle_ph_extend(self, **options):
        if options.get("celery"):
            return self._dispatch_celery_ph_extend(**options)

        from apps.pricing.backfill.phase3_extend import extend_with_pricehistory

        self.stdout.write(self.style.MIGRATE_HEADING("Phase 3: PH deep history extension"))
        result = asyncio.run(
            extend_with_pricehistory(
                limit=options.get("limit", 5000),
                marketplace_slug=options.get("marketplace"),
                delay=options.get("delay"),
            )
        )
        self._print_result("Phase 3", result)

    def _dispatch_celery_ph_extend(self, **options):
        from apps.pricing.tasks import run_phase3_extend

        workers = options.get("workers", 4)
        limit = options.get("limit", 5000)
        marketplace = options.get("marketplace")
        delay = options.get("delay")

        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Phase 3: Dispatching {workers} Celery tasks (limit={limit} each)"
        ))

        task_ids = []
        for i in range(workers):
            result = run_phase3_extend.apply_async(
                kwargs={
                    "limit": limit,
                    "marketplace_slug": marketplace,
                    "delay": delay,
                },
            )
            task_ids.append(result.id)
            self.stdout.write(f"  Worker {i + 1}: task_id={result.id}")

        self.stdout.write(self.style.SUCCESS(
            f"\nDispatched {workers} ph-extend tasks to Celery. "
            f"Each claims up to {limit} products via SKIP LOCKED.\n"
            f"Monitor via: celery -A whydud inspect active\n"
            f"Or Flower dashboard."
        ))

    # ── Phase 4a: Scrape ─────────────────────────────────────────

    def _handle_scrape(self, **options):
        from apps.pricing.backfill.targeted_scrape import scrape_backfill_products

        self.stdout.write(self.style.MIGRATE_HEADING("Phase 4a: Targeted scrape"))
        result = scrape_backfill_products(
            batch_size=options.get("batch"),
            marketplace_slug=options.get("marketplace"),
            limit=options.get("limit"),
            dry_run=options.get("dry_run", False),
            include_retried=options.get("include_retried", False),
            auto_inject=options.get("inject", False),
        )
        self._print_result("Scrape", result)

    # ── Phase 4b: Inject ─────────────────────────────────────────

    def _handle_inject(self, **options):
        from apps.pricing.backfill.phase4_inject import inject_cached_data

        self.stdout.write(self.style.MIGRATE_HEADING("Phase 4: Inject cached price data"))
        result = inject_cached_data(
            batch_size=options.get("batch", 5000),
            marketplace_slug=options.get("marketplace"),
            dry_run=options.get("dry_run", False),
        )
        self._print_result("Phase 4", result)

    # ── Lightweight record creator ────────────────────────────────

    def _handle_create_lightweight(self, **options):
        from apps.pricing.backfill.lightweight_creator import create_lightweight_records

        batch_size = options.get("batch", 1000)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Lightweight record creator (batch={batch_size})"
        ))

        total_stats = {
            "created": 0, "linked": 0, "skipped": 0,
            "errors": 0, "snapshots_injected": 0,
        }
        iteration = 0

        while True:
            iteration += 1
            self.stdout.write(f"\n  Iteration {iteration}...")
            result = create_lightweight_records(batch_size=batch_size)

            for key in total_stats:
                total_stats[key] += result.get(key, 0)

            processed = result["created"] + result["linked"] + result["skipped"] + result["errors"]
            if processed == 0:
                self.stdout.write("  No more candidates — done.")
                break

            self.stdout.write(
                f"  Batch: {result['created']} created, {result['linked']} linked, "
                f"{result['skipped']} skipped, {result['errors']} errors, "
                f"{result['snapshots_injected']:,} snapshots"
            )

        self._print_result("Lightweight creator", total_stats)

    # ── Assign Priorities ────────────────────────────────────────

    def _handle_assign_priorities(self, **options):
        from apps.pricing.backfill.prioritizer import (
            assign_enrichment_priorities,
            assign_review_targets,
            populate_derived_fields,
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Populating derived fields"))
        pop_result = populate_derived_fields()
        self.stdout.write(
            f"  Prices filled: {pop_result['price_filled']:,}  |  "
            f"Categories inferred: {pop_result['category_filled']:,}"
        )

        self.stdout.write(self.style.MIGRATE_HEADING("Assigning enrichment priorities"))
        result = assign_enrichment_priorities()
        self.stdout.write(
            f"  P1 (Playwright): {result['p1']:,}  |  P2 (curl_cffi): {result['p2']:,}"
        )

        max_review = options.get("max_review", 100_000)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Assigning review targets (max={max_review:,})"
        ))
        review_total = assign_review_targets(max_review_products=max_review)
        self.stdout.write(f"  Review targets assigned: {review_total:,}")
        self.stdout.write(self.style.SUCCESS("Priority assignment complete."))

    # ── Enrichment ─────────────────────────────────────────────

    def _handle_enrich(self, **options):
        from apps.pricing.backfill.enrichment import (
            enrich_batch,
            enrich_single_product,
        )

        product_id = options.get("product_id")
        if product_id:
            self.stdout.write(f"Enriching single product: {product_id}")
            result = enrich_single_product(product_id)
            self._print_result("Enrich single", result)
            return

        batch_size = options.get("batch", 100)
        self.stdout.write(self.style.MIGRATE_HEADING(
            f"Enrichment batch (size={batch_size})"
        ))
        result = enrich_batch(batch_size=batch_size)
        self._print_result("Enrichment batch", result)

    # ── Status ───────────────────────────────────────────────────

    def _handle_status(self, **options):
        import json as json_mod
        import time as time_mod

        watch = options.get("watch", False)
        json_output = options.get("json_output", False)

        if watch and json_output:
            self.stderr.write("--watch and --json cannot be combined.")
            sys.exit(1)

        while True:
            data = self._collect_status_data()
            if json_output:
                self.stdout.write(json_mod.dumps(data, indent=2, default=str))
                return
            self._print_status_dashboard(data)
            if not watch:
                return
            try:
                self.stdout.write("\n  Refreshing in 30s... (Ctrl+C to stop)")
                time_mod.sleep(30)
                # Clear screen
                self.stdout.write("\033[2J\033[H", ending="")
            except KeyboardInterrupt:
                self.stdout.write("\n")
                return

    def _collect_status_data(self) -> dict:
        """Gather all pipeline metrics into a single dict."""
        from apps.pricing.backfill.config import BackfillConfig
        from apps.pricing.backfill.injector import count_snapshots_by_source
        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product, ProductListing

        data: dict = {}

        # -- BackfillProduct total + by status --
        total = BackfillProduct.objects.count()
        data["total"] = total

        by_status = {}
        for status in BackfillProduct.Status:
            cnt = BackfillProduct.objects.filter(status=status.value).count()
            if cnt > 0:
                by_status[status.label] = cnt
        data["by_status"] = by_status

        # -- By marketplace --
        by_marketplace = {}
        for row in (
            BackfillProduct.objects
            .values("marketplace_slug")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        ):
            by_marketplace[row["marketplace_slug"]] = row["cnt"]
        data["by_marketplace"] = by_marketplace

        # -- Scrape status --
        max_retries = BackfillConfig.scrape_max_retries()
        scrape_status = {}
        for ss in BackfillProduct.ScrapeStatus:
            cnt = BackfillProduct.objects.filter(scrape_status=ss.value).count()
            if cnt > 0:
                scrape_status[ss.label] = cnt
        # Split failed into retryable vs exhausted
        failed_retryable = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__lt=max_retries,
        ).count()
        failed_exhausted = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__gte=max_retries,
        ).count()
        scrape_status["Failed (retryable)"] = failed_retryable
        scrape_status["Failed (exhausted)"] = failed_exhausted
        data["scrape_status"] = scrape_status

        # -- Enrichment priority (pending scrape_status only) --
        priority_labels = {
            0: "P0 (on-demand)", 1: "P1 (Playwright)",
            2: "P2 (curl_cffi)", 3: "P3 (curl_cffi-low)",
        }
        by_priority = {}
        for row in (
            BackfillProduct.objects.filter(scrape_status="pending")
            .values("enrichment_priority")
            .annotate(cnt=Count("id"))
            .order_by("enrichment_priority")
        ):
            label = priority_labels.get(row["enrichment_priority"], f"P{row['enrichment_priority']}")
            by_priority[label] = row["cnt"]
        data["enrichment_priority"] = by_priority

        # -- Enrichment method distribution (completed) --
        by_method = {}
        for row in (
            BackfillProduct.objects.filter(scrape_status="scraped")
            .values("enrichment_method")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
        ):
            by_method[row["enrichment_method"]] = row["cnt"]
        data["enrichment_method"] = by_method

        # -- Review status --
        by_review = {}
        for rs in BackfillProduct.ReviewStatus:
            cnt = BackfillProduct.objects.filter(review_status=rs.value).count()
            if cnt > 0:
                by_review[rs.label] = cnt
        data["review_status"] = by_review

        # -- Products summary --
        product_total = Product.objects.count()
        lightweight = Product.objects.filter(is_lightweight=True).count()
        with_reviews = Product.objects.filter(total_reviews__gt=0).count()
        with_dudscore = Product.objects.filter(dud_score__isnull=False).count()
        data["products"] = {
            "total": product_total,
            "lightweight": lightweight,
            "enriched": product_total - lightweight,
            "with_reviews": with_reviews,
            "with_dudscore": with_dudscore,
        }

        # -- Price snapshots by source --
        source_counts = count_snapshots_by_source()
        data["snapshots_by_source"] = source_counts
        data["snapshots_total"] = sum(source_counts.values())

        # -- Existing listing coverage --
        supported = list(BackfillConfig.bh_pos_map().keys())
        eligible = ProductListing.objects.filter(
            marketplace__slug__in=supported,
        ).exclude(external_id="").count()

        with connection.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT listing_id) FROM price_snapshots WHERE source = 'buyhatke'"
            )
            bh_covered = cur.fetchone()[0]
        data["listings"] = {"eligible": eligible, "bh_covered": bh_covered}

        # -- Estimated times --
        pending_p1 = by_priority.get("P1 (Playwright)", 0)
        pending_p2 = by_priority.get("P2 (curl_cffi)", 0) + by_priority.get("P3 (curl_cffi-low)", 0)
        review_pending = BackfillProduct.objects.filter(review_status="pending").count()

        # Playwright: ~30s/product, curl_cffi: ~2s/product, reviews: ~15s/product
        est_p1_hours = (pending_p1 * 30) / 3600
        est_p2_hours = (pending_p2 * 2) / 3600
        est_review_hours = (review_pending * 15) / 3600
        data["estimates"] = {
            "p1_playwright_hours": round(est_p1_hours, 1),
            "p2_curlffi_hours": round(est_p2_hours, 1),
            "review_hours": round(est_review_hours, 1),
            "total_hours": round(est_p1_hours + est_p2_hours + est_review_hours, 1),
        }

        return data

    def _print_status_dashboard(self, data: dict) -> None:
        """Pretty-print the comprehensive status dashboard."""
        from datetime import datetime

        w = self.stdout.write
        heading = self.style.MIGRATE_HEADING
        success = self.style.SUCCESS

        w(heading(f"BACKFILL PIPELINE STATUS — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        w("")

        total = data["total"]
        w(f"  BackfillProduct total: {total:,}")
        w("")

        # -- BY STATUS --
        if data["by_status"]:
            w("  BY STATUS:")
            for label, cnt in data["by_status"].items():
                bar = "#" * min(cnt * 40 // max(total, 1), 40)
                w(f"    {label:<20} {cnt:>8,}  {bar}")
            w("")

        # -- BY MARKETPLACE --
        if data["by_marketplace"]:
            w("  BY MARKETPLACE:")
            for slug, cnt in data["by_marketplace"].items():
                w(f"    {slug:<20} {cnt:>8,}")
            w("")

        # -- SCRAPE STATUS --
        if data["scrape_status"]:
            w("  SCRAPE STATUS:")
            for label, cnt in data["scrape_status"].items():
                if cnt > 0:
                    w(f"    {label:<25} {cnt:>8,}")
            w("")

        # -- ENRICHMENT PRIORITY --
        if data["enrichment_priority"]:
            w("  ENRICHMENT PRIORITY (pending):")
            for label, cnt in data["enrichment_priority"].items():
                w(f"    {label:<25} {cnt:>8,}")
            w("")

        # -- ENRICHMENT METHOD (completed) --
        if data["enrichment_method"]:
            w("  ENRICHMENT METHOD (scraped):")
            for method, cnt in data["enrichment_method"].items():
                w(f"    {method:<25} {cnt:>8,}")
            w("")

        # -- REVIEW STATUS --
        if data["review_status"]:
            w("  REVIEW STATUS:")
            for label, cnt in data["review_status"].items():
                w(f"    {label:<25} {cnt:>8,}")
            w("")

        # -- PRODUCTS --
        p = data["products"]
        w("  PRODUCTS:")
        w(f"    {'Total':<25} {p['total']:>8,}")
        w(f"    {'Lightweight':<25} {p['lightweight']:>8,}")
        w(f"    {'Enriched':<25} {p['enriched']:>8,}")
        w(f"    {'With reviews':<25} {p['with_reviews']:>8,}")
        w(f"    {'With DudScore':<25} {p['with_dudscore']:>8,}")
        w("")

        # -- PRICE SNAPSHOTS --
        w("  PRICE SNAPSHOTS BY SOURCE:")
        for source, cnt in sorted(data["snapshots_by_source"].items(), key=lambda x: -x[1]):
            w(f"    {source:<22} {cnt:>12,}")
        w(f"    {'TOTAL':<22} {data['snapshots_total']:>12,}")
        w("")

        # -- LISTINGS --
        l = data["listings"]
        w(f"  EXISTING LISTINGS: {l['eligible']:,} eligible, {l['bh_covered']:,} BH-covered")
        w("")

        # -- ESTIMATED TIMES --
        e = data["estimates"]
        w("  ESTIMATED TIME REMAINING:")
        w(f"    P1 Playwright:       {e['p1_playwright_hours']:>8.1f} hrs")
        w(f"    P2/P3 curl_cffi:     {e['p2_curlffi_hours']:>8.1f} hrs")
        w(f"    Reviews:             {e['review_hours']:>8.1f} hrs")
        w(success(f"    Total (sequential):  {e['total_hours']:>8.1f} hrs"))

    # ── Retry Failed (granular) ──────────────────────────────────

    def _handle_retry_failed(self, **options):
        from django.db.models import F

        from apps.pricing.models import BackfillProduct

        dry_run = options.get("dry_run", False)
        do_scrape = options.get("scrape", False)
        do_reviews = options.get("reviews", False)
        do_history = options.get("history", False)

        if not (do_scrape or do_reviews or do_history):
            self.stderr.write(
                "Specify at least one of: --scrape, --reviews, --history"
            )
            sys.exit(1)

        w = self.stdout.write
        prefix = "[DRY RUN] " if dry_run else ""

        if do_scrape:
            qs = BackfillProduct.objects.filter(scrape_status="failed")
            count = qs.count()
            w(f"{prefix}Failed enrichments: {count:,}")
            if count and not dry_run:
                qs.update(
                    scrape_status="pending",
                    error_message="",
                    retry_count=F("retry_count") + 1,
                )
                w(self.style.SUCCESS(f"  Reset {count:,} to pending (retry_count incremented)"))

        if do_reviews:
            qs = BackfillProduct.objects.filter(review_status="failed")
            count = qs.count()
            w(f"{prefix}Failed review scrapes: {count:,}")
            if count and not dry_run:
                qs.update(
                    review_status="pending",
                    error_message="",
                    retry_count=F("retry_count") + 1,
                )
                w(self.style.SUCCESS(f"  Reset {count:,} to pending (retry_count incremented)"))

        if do_history:
            qs = BackfillProduct.objects.filter(status="failed")
            count = qs.count()
            w(f"{prefix}Failed history fetches: {count:,}")
            if count and not dry_run:
                qs.update(
                    status="discovered",
                    error_message="",
                    retry_count=F("retry_count") + 1,
                )
                w(self.style.SUCCESS(f"  Reset {count:,} to discovered (retry_count incremented)"))

            # Also recover stale claims from crashed parallel workers
            from django.utils import timezone
            from datetime import timedelta
            stale_cutoff = timezone.now() - timedelta(hours=1)

            stale_bh = BackfillProduct.objects.filter(
                status="bh_filling", updated_at__lt=stale_cutoff
            )
            stale_bh_count = stale_bh.count()
            if stale_bh_count:
                w(f"{prefix}Stale bh_filling claims (>1hr): {stale_bh_count:,}")
                if not dry_run:
                    stale_bh.update(status="discovered")
                    w(self.style.SUCCESS(f"  Released {stale_bh_count:,} back to discovered"))

            stale_ph = BackfillProduct.objects.filter(
                status="ph_extending", updated_at__lt=stale_cutoff
            )
            stale_ph_count = stale_ph.count()
            if stale_ph_count:
                w(f"{prefix}Stale ph_extending claims (>1hr): {stale_ph_count:,}")
                if not dry_run:
                    stale_ph.update(status="bh_filled")
                    w(self.style.SUCCESS(f"  Released {stale_ph_count:,} back to bh_filled"))

    # ── Skip Products ─────────────────────────────────────────────

    def _handle_skip_products(self, **options):
        import re as re_mod

        from apps.pricing.models import BackfillProduct

        dry_run = options.get("dry_run", False)
        price_below = options.get("price_below")
        category = options.get("category")
        prefix = "[DRY RUN] " if dry_run else ""
        w = self.stdout.write

        if not (price_below or category):
            self.stderr.write("Specify at least one of: --price-below, --category")
            sys.exit(1)

        base_qs = BackfillProduct.objects.filter(scrape_status="pending")

        total_skipped = 0

        if price_below:
            qs = base_qs.filter(current_price__lt=price_below, current_price__gt=0)
            count = qs.count()
            w(f"{prefix}Products with price < {price_below} paisa (Rs.{price_below / 100:.0f}): {count:,}")
            if count and not dry_run:
                qs.update(scrape_status="failed", error_message=f"Skipped: price below {price_below} paisa")
                w(self.style.SUCCESS(f"  Marked {count:,} as failed (skipped)"))
                total_skipped += count

        if category:
            # Validate regex
            try:
                re_mod.compile(category, re_mod.IGNORECASE)
            except re_mod.error as e:
                self.stderr.write(f"Invalid regex pattern: {e}")
                sys.exit(1)

            qs = base_qs.filter(category_name__iregex=category)
            count = qs.count()
            w(f"{prefix}Products matching category '{category}': {count:,}")
            if count and not dry_run:
                qs.update(
                    scrape_status="failed",
                    error_message=f"Skipped: category matches '{category}'",
                )
                w(self.style.SUCCESS(f"  Marked {count:,} as failed (skipped)"))
                total_skipped += count

        if not dry_run:
            w(f"\n  Total skipped: {total_skipped:,}")

    # ── Run Overnight ─────────────────────────────────────────────

    def _handle_run_overnight(self, **options):
        import time as time_mod
        from datetime import datetime, timedelta

        from zoneinfo import ZoneInfo

        from apps.pricing.backfill.enrichment import enrich_batch
        from apps.pricing.models import BackfillProduct

        ist = ZoneInfo("Asia/Kolkata")
        stop_at_str = options.get("stop_at", "06:00")
        batch_size = options.get("batch", 100)
        progress_interval = options.get("progress_interval", 300)

        # Parse stop time
        try:
            stop_h, stop_m = map(int, stop_at_str.split(":"))
        except (ValueError, AttributeError):
            self.stderr.write(f"Invalid --stop-at format: {stop_at_str} (expected HH:MM)")
            sys.exit(1)

        now_ist = datetime.now(ist)
        stop_time = now_ist.replace(hour=stop_h, minute=stop_m, second=0, microsecond=0)
        # If stop time is in the past, assume next day
        if stop_time <= now_ist:
            stop_time += timedelta(days=1)

        w = self.stdout.write
        heading = self.style.MIGRATE_HEADING

        w(heading("OVERNIGHT ENRICHMENT RUNNER"))
        w(f"  Started:    {now_ist.strftime('%Y-%m-%d %H:%M IST')}")
        w(f"  Stop at:    {stop_time.strftime('%Y-%m-%d %H:%M IST')}")
        w(f"  Batch size: {batch_size}")
        w("")

        # Step 1: Auto assign-priorities if P1 count is 0
        p1_count = BackfillProduct.objects.filter(
            scrape_status="pending", enrichment_priority=1,
        ).count()

        if p1_count == 0:
            w(heading("Step 1: Assigning priorities (P1 count is 0)"))
            from apps.pricing.backfill.prioritizer import (
                assign_enrichment_priorities,
                assign_review_targets,
                populate_derived_fields,
            )

            pop_result = populate_derived_fields()
            w(f"  Derived fields: {pop_result['price_filled']:,} prices, {pop_result['category_filled']:,} categories")

            result = assign_enrichment_priorities()
            w(f"  P1: {result['p1']:,}  |  P2: {result['p2']:,}")

            review_total = assign_review_targets()
            w(f"  Review targets: {review_total:,}")
            w("")
        else:
            w(f"  P1 pending: {p1_count:,} (skipping priority assignment)")
            w("")

        # Tracking
        total_dispatched = 0
        batches_run = 0
        last_progress = time_mod.monotonic()
        start_time = time_mod.monotonic()

        # Snapshot initial counts
        initial_scraped = BackfillProduct.objects.filter(scrape_status="scraped").count()

        w(heading("Step 2: Running enrichment batches"))

        try:
            while True:
                # Check stop time
                now = datetime.now(ist)
                if now >= stop_time:
                    w(f"\n  Stop time reached ({stop_at_str} IST)")
                    break

                # Check remaining work
                remaining = BackfillProduct.objects.filter(
                    scrape_status="pending",
                ).exclude(marketplace_url="").count()

                if remaining == 0:
                    w("\n  No more pending products — done!")
                    break

                # Dispatch batch
                result = enrich_batch(batch_size=batch_size)
                dispatched = result.get("dispatched", 0)
                total_dispatched += dispatched
                batches_run += 1

                if dispatched == 0:
                    w("\n  No products dispatched — waiting 60s...")
                    time_mod.sleep(60)
                    continue

                # Progress report every N seconds
                elapsed = time_mod.monotonic() - last_progress
                if elapsed >= progress_interval:
                    current_scraped = BackfillProduct.objects.filter(
                        scrape_status="scraped"
                    ).count()
                    newly_scraped = current_scraped - initial_scraped
                    pending = BackfillProduct.objects.filter(scrape_status="pending").count()
                    failed = BackfillProduct.objects.filter(scrape_status="failed").count()
                    time_remaining = (stop_time - datetime.now(ist)).total_seconds() / 3600

                    w(
                        f"\n  [{now.strftime('%H:%M')}] "
                        f"Dispatched: {total_dispatched:,} | "
                        f"Scraped: +{newly_scraped:,} | "
                        f"Pending: {pending:,} | "
                        f"Failed: {failed:,} | "
                        f"Time left: {time_remaining:.1f}h"
                    )
                    last_progress = time_mod.monotonic()

                # Wait between batches — let Celery workers process
                # P1 (Playwright) is slow (~30s/product), so wait longer
                time_mod.sleep(30)

        except KeyboardInterrupt:
            w("\n  Interrupted by user.")

        # Final summary
        total_elapsed = (time_mod.monotonic() - start_time) / 3600
        final_scraped = BackfillProduct.objects.filter(scrape_status="scraped").count()
        newly_scraped = final_scraped - initial_scraped
        final_pending = BackfillProduct.objects.filter(scrape_status="pending").count()
        final_failed = BackfillProduct.objects.filter(scrape_status="failed").count()

        w("")
        w(heading("OVERNIGHT RUN SUMMARY"))
        w(f"  Duration:         {total_elapsed:.1f} hours")
        w(f"  Batches run:      {batches_run:,}")
        w(f"  Tasks dispatched: {total_dispatched:,}")
        w(f"  Newly scraped:    {newly_scraped:,}")
        w(f"  Still pending:    {final_pending:,}")
        w(f"  Failed:           {final_failed:,}")
        w(self.style.SUCCESS("  Overnight run complete."))

    # ── Verify Data ───────────────────────────────────────────────

    def _handle_verify_data(self, **options):
        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product, ProductListing
        from apps.reviews.models import Review

        w = self.stdout.write
        heading = self.style.MIGRATE_HEADING
        warning = self.style.WARNING

        w(heading("DATA QUALITY VERIFICATION"))
        issues_found = 0

        # 1. is_lightweight=True but listing.last_scraped_at is not NULL
        w("\n  1. Lightweight products with last_scraped_at set:")
        count = Product.objects.filter(
            is_lightweight=True,
            listings__last_scraped_at__isnull=False,
        ).distinct().count()
        if count:
            w(warning(f"     WARN: {count:,} products marked lightweight but have been scraped"))
            issues_found += 1
        else:
            w("     OK")

        # 2. scrape_status='scraped' but product_listing is NULL
        w("\n  2. Scraped BackfillProducts without product_listing:")
        count = BackfillProduct.objects.filter(
            scrape_status="scraped",
            product_listing__isnull=True,
        ).count()
        if count:
            w(warning(f"     WARN: {count:,} scraped records with no product_listing link"))
            issues_found += 1
        else:
            w("     OK")

        # 3. review_status='scraped' but 0 reviews in DB
        w("\n  3. Review-scraped BackfillProducts with 0 reviews:")
        review_scraped = BackfillProduct.objects.filter(
            review_status="scraped",
        ).select_related("product_listing")
        zero_reviews = 0
        for bp in review_scraped.iterator(chunk_size=1000):
            if bp.product_listing:
                rc = Review.objects.filter(
                    product_id=bp.product_listing.product_id,
                ).count()
                if rc == 0:
                    zero_reviews += 1
        if zero_reviews:
            w(warning(f"     WARN: {zero_reviews:,} marked review_status=scraped but have 0 reviews"))
            issues_found += 1
        else:
            w("     OK")

        # 4. Duplicate (marketplace_slug, external_id)
        w("\n  4. Duplicate (marketplace_slug, external_id) pairs:")
        with connection.cursor() as cur:
            cur.execute("""
                SELECT marketplace_slug, external_id, COUNT(*) AS cnt
                FROM backfill_products
                GROUP BY marketplace_slug, external_id
                HAVING COUNT(*) > 1
                ORDER BY cnt DESC
                LIMIT 20
            """)
            dupes = cur.fetchall()
        if dupes:
            total_dupe_groups = len(dupes)
            w(warning(f"     WARN: {total_dupe_groups} duplicate groups found"))
            for slug, ext_id, cnt in dupes[:5]:
                w(f"       {slug}/{ext_id}: {cnt} copies")
            if total_dupe_groups > 5:
                w(f"       ... and {total_dupe_groups - 5} more")
            issues_found += 1
        else:
            w("     OK")

        # 5. Products with current_price=0 or NULL
        w("\n  5. Products with current_price=0 or NULL:")
        from django.db.models import Q as Q_filter
        count = BackfillProduct.objects.filter(
            Q_filter(current_price=0) | Q_filter(current_price__isnull=True),
            scrape_status="pending",
        ).count()
        if count:
            w(warning(f"     WARN: {count:,} pending products with zero/null price"))
            issues_found += 1
        else:
            w("     OK")

        # 6. BackfillProduct with product_listing pointing to deleted Product
        w("\n  6. Orphaned BackfillProducts (listing points to deleted product):")
        orphaned = BackfillProduct.objects.filter(
            product_listing__isnull=False,
        ).exclude(
            product_listing__product__in=Product.objects.all(),
        ).count()
        if orphaned:
            w(warning(f"     WARN: {orphaned:,} backfill records with orphaned product_listing"))
            issues_found += 1
        else:
            w("     OK")

        # Summary
        w("")
        if issues_found:
            w(warning(f"  {issues_found} issue(s) found. Review warnings above."))
        else:
            w(self.style.SUCCESS("  All checks passed — no issues found."))

    # ── Reset Failed ─────────────────────────────────────────────

    def _handle_reset_failed(self, **options):
        from apps.pricing.models import BackfillProduct

        count = BackfillProduct.objects.filter(status="failed").count()
        if count == 0:
            self.stdout.write("No failed BackfillProducts to reset.")
            return

        self.stdout.write(f"Will reset {count} failed BackfillProducts to 'discovered'.")
        BackfillProduct.objects.filter(status="failed").update(
            status="discovered", error_message="", retry_count=0
        )
        self.stdout.write(self.style.SUCCESS(f"Reset {count} products."))

    # ── Refresh Aggregate ────────────────────────────────────────

    def _handle_refresh_aggregate(self, **options):
        self.stdout.write("Refreshing price_daily continuous aggregate...")
        with connection.cursor() as cur:
            cur.execute("CALL refresh_continuous_aggregate('price_daily', NULL, NULL);")
        self.stdout.write(self.style.SUCCESS("Done."))

    # ── Helpers ──────────────────────────────────────────────────

    def _print_result(self, phase: str, result: dict) -> None:
        """Pretty-print a phase result dict."""
        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS(f"{phase} complete:"))
        for key, val in result.items():
            if isinstance(val, int) and val > 999:
                self.stdout.write(f"  {key}: {val:,}")
            else:
                self.stdout.write(f"  {key}: {val}")
        self.stdout.write("")
