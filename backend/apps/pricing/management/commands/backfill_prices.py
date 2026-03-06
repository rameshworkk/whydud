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
