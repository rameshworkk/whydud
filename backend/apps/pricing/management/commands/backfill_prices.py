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
        sub.add_parser("status", help="Show backfill pipeline status dashboard")
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
        from apps.pricing.backfill.injector import count_snapshots_by_source
        from apps.pricing.models import BackfillProduct

        self.stdout.write(self.style.MIGRATE_HEADING("BACKFILL STATUS"))
        self.stdout.write("")

        # BackfillProduct counts by status
        total = BackfillProduct.objects.count()
        self.stdout.write(f"  BackfillProduct total: {total:,}")
        if total > 0:
            self.stdout.write("  BY STATUS:")
            for status in BackfillProduct.Status:
                count = BackfillProduct.objects.filter(status=status.value).count()
                if count > 0:
                    bar = "#" * min(count * 40 // total, 40) if total > 0 else ""
                    self.stdout.write(f"    {status.label:<20} {count:>8,}  {bar}")

            self.stdout.write("")
            self.stdout.write("  BY MARKETPLACE:")
            for row in (
                BackfillProduct.objects
                .values("marketplace_slug")
                .annotate(cnt=Count("id"))
                .order_by("-cnt")
            ):
                self.stdout.write(f"    {row['marketplace_slug']:<20} {row['cnt']:>8,}")

        # price_snapshots counts by source
        self.stdout.write("")
        self.stdout.write("  PRICE_SNAPSHOTS BY SOURCE:")
        source_counts = count_snapshots_by_source()
        snapshot_total = sum(source_counts.values())
        for source, count in sorted(source_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"    {source:<22} {count:>12,}")
        self.stdout.write(f"    {'TOTAL':<22} {snapshot_total:>12,}")

        # Existing ProductListing coverage
        from apps.products.models import ProductListing
        from apps.pricing.backfill.config import BackfillConfig

        supported = list(BackfillConfig.bh_pos_map().keys())
        eligible = ProductListing.objects.filter(
            marketplace__slug__in=supported,
        ).exclude(external_id="").count()

        with connection.cursor() as cur:
            cur.execute(
                "SELECT COUNT(DISTINCT listing_id) FROM price_snapshots WHERE source = 'buyhatke'"
            )
            bh_covered = cur.fetchone()[0]

        self.stdout.write("")
        self.stdout.write(f"  EXISTING LISTINGS: {eligible:,} eligible, {bh_covered:,} BH-covered")

        # Phase 4 injectable candidates
        injectable = BackfillProduct.objects.filter(
            status__in=["bh_filled", "ph_extended"],
            product_listing__isnull=True,
        ).exclude(raw_price_data=[]).exclude(external_id="").count()

        with_cache = BackfillProduct.objects.exclude(raw_price_data=[]).count()
        self.stdout.write("")
        self.stdout.write(f"  CACHED DATA: {with_cache:,} products with raw_price_data")
        self.stdout.write(f"  INJECTABLE: {injectable:,} candidates for Phase 4 inject")

        # Scrape status
        from apps.pricing.backfill.config import BackfillConfig as BConfig
        max_retries = BConfig.scrape_max_retries()
        pending = BackfillProduct.objects.filter(scrape_status="pending").exclude(external_id="").count()
        scraped = BackfillProduct.objects.filter(scrape_status="scraped").count()
        failed_retryable = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__lt=max_retries,
        ).count()
        failed_exhausted = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__gte=max_retries,
        ).count()

        self.stdout.write("")
        self.stdout.write("  SCRAPE STATUS:")
        self.stdout.write(f"    {'pending':<25} {pending:>8,}  (never attempted)")
        self.stdout.write(f"    {'scraped':<25} {scraped:>8,}  (ProductListing created)")
        self.stdout.write(f"    {'failed (retry < {0})':<25} {failed_retryable:>8,}  (eligible for retry)".format(max_retries))
        self.stdout.write(f"    {'failed (retry >= {0})':<25} {failed_exhausted:>8,}  (deprioritized)".format(max_retries))

        # Enrichment priority distribution
        self.stdout.write("")
        self.stdout.write("  ENRICHMENT PRIORITY (pending only):")
        priority_labels = {0: "P0 (on-demand)", 1: "P1 (Playwright)", 2: "P2 (curl_cffi)", 3: "P3 (curl_cffi-low)"}
        for row in (
            BackfillProduct.objects.filter(scrape_status="pending")
            .values("enrichment_priority")
            .annotate(cnt=Count("id"))
            .order_by("enrichment_priority")
        ):
            label = priority_labels.get(row["enrichment_priority"], f"P{row['enrichment_priority']}")
            self.stdout.write(f"    {label:<25} {row['cnt']:>8,}")

        # Review status
        self.stdout.write("")
        self.stdout.write("  REVIEW STATUS:")
        for rs in BackfillProduct.ReviewStatus:
            cnt = BackfillProduct.objects.filter(review_status=rs.value).count()
            if cnt > 0:
                self.stdout.write(f"    {rs.label:<25} {cnt:>8,}")

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
