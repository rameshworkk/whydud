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

    # Phase 3: PH deep history extension for top products
    python manage.py backfill_prices ph-extend --limit 5000

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
        p1.add_argument("--no-filter", action="store_true", help="Skip electronics keyword filter")
        p1.add_argument("--delay", type=float, default=None, help="Override PH request delay")

        # ── Phase 2: bh-fill ─────────────────────────────────────
        p2 = sub.add_parser("bh-fill", help="BuyHatke bulk price history fill")
        p2.add_argument("--batch", type=int, default=5000, help="Batch size")
        p2.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p2.add_argument("--delay", type=float, default=None, help="Override BH request delay")

        # ── Phase 3: ph-extend ───────────────────────────────────
        p3 = sub.add_parser("ph-extend", help="Extend top products with PH deep history")
        p3.add_argument("--limit", type=int, default=5000, help="Max products to extend")
        p3.add_argument("--marketplace", type=str, default=None, help="Filter by marketplace slug")
        p3.add_argument("--delay", type=float, default=None, help="Override PH request delay")

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
                filter_electronics=not options.get("no_filter", False),
                max_products=options.get("limit"),
                delay=options.get("delay"),
            )
        )
        self._print_result("Phase 1", result)

    # ── Phase 2 ──────────────────────────────────────────────────

    def _handle_bh_fill(self, **options):
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

    # ── Phase 3 ──────────────────────────────────────────────────

    def _handle_ph_extend(self, **options):
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
