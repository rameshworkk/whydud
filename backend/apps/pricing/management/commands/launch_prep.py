"""Management command to prepare the platform for launch.

Subcommands:
    status          Show current pipeline status and launch readiness
    prioritize      Tag top N products for priority enrichment
    analyze-failed  Analyze failure patterns and show actionable fixes
    reset-retryable Reset retryable failures for re-processing
    boost-enrich    Run continuous enrichment at higher throughput
    sync-search     Sync all products (including lightweight) to Meilisearch

Usage::

    python manage.py launch_prep status
    python manage.py launch_prep prioritize --top 5000
    python manage.py launch_prep analyze-failed
    python manage.py launch_prep reset-retryable
    python manage.py launch_prep boost-enrich --batch 500 --rounds 20
    python manage.py launch_prep sync-search
"""
from __future__ import annotations

import logging
import time
from collections import Counter

from django.core.management.base import BaseCommand
from django.db.models import Count, Q, Sum
from django.utils import timezone

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Launch preparation: status, prioritize, fix failures, boost enrichment"

    def add_arguments(self, parser):
        sub = parser.add_subparsers(dest="subcommand")
        sub.required = True

        # ── status ──
        sub.add_parser("status", help="Show pipeline status and launch readiness")

        # ── prioritize ──
        p = sub.add_parser("prioritize", help="Tag top N products for priority enrichment")
        p.add_argument("--top", type=int, default=5000, help="Number of top products to prioritize (default 5000)")
        p.add_argument("--dry-run", action="store_true", help="Show what would be changed")

        # ── analyze-failed ──
        af = sub.add_parser("analyze-failed", help="Analyze failure patterns")
        af.add_argument("--limit", type=int, default=100, help="Number of failures to sample")

        # ── reset-retryable ──
        rr = sub.add_parser("reset-retryable", help="Reset retryable failures")
        rr.add_argument("--all", action="store_true", help="Reset ALL failures (not just retryable)")
        rr.add_argument("--type", choices=["pipeline", "enrichment", "reviews", "all"], default="all")
        rr.add_argument("--dry-run", action="store_true")

        # ── boost-enrich ──
        be = sub.add_parser("boost-enrich", help="Run continuous enrichment batches")
        be.add_argument("--batch", type=int, default=500, help="Batch size per round")
        be.add_argument("--rounds", type=int, default=10, help="Number of rounds")
        be.add_argument("--delay", type=int, default=5, help="Seconds between rounds")
        be.add_argument("--priority", type=int, default=None, help="Only enrich this priority level (1/2/3)")

        # ── sync-search ──
        ss = sub.add_parser("sync-search", help="Sync all products to Meilisearch")
        ss.add_argument("--lightweight-only", action="store_true", help="Only sync lightweight products")

    def handle(self, *args, **options):
        cmd = options["subcommand"]
        if cmd == "status":
            self._status()
        elif cmd == "prioritize":
            self._prioritize(options["top"], options["dry_run"])
        elif cmd == "analyze-failed":
            self._analyze_failed(options["limit"])
        elif cmd == "reset-retryable":
            self._reset_retryable(options["all"], options["type"], options["dry_run"])
        elif cmd == "boost-enrich":
            self._boost_enrich(
                options["batch"], options["rounds"],
                options["delay"], options["priority"],
            )
        elif cmd == "sync-search":
            self._sync_search(options.get("lightweight_only", False))

    # ──────────────────────────────────────────────────────────────────
    # STATUS
    # ──────────────────────────────────────────────────────────────────

    def _status(self):
        from apps.pricing.models import BackfillProduct
        from apps.products.models import Product

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("  WHYDUD LAUNCH READINESS STATUS")
        self.stdout.write("=" * 70)

        # Product counts
        total_products = Product.objects.count()
        lightweight = Product.objects.filter(is_lightweight=True).count()
        enriched = Product.objects.filter(is_lightweight=False).count()
        with_price = Product.objects.filter(current_best_price__isnull=False).count()
        with_images = Product.objects.exclude(images=[]).exclude(images__isnull=True).count()
        with_rating = Product.objects.filter(avg_rating__isnull=False).count()
        active = Product.objects.filter(status="active").count()

        self.stdout.write(f"\n  PRODUCTS (in Product table):")
        self.stdout.write(f"    Total:          {total_products:>10,}")
        self.stdout.write(f"    Active:         {active:>10,}")
        self.stdout.write(f"    Enriched:       {enriched:>10,}  (is_lightweight=False)")
        self.stdout.write(f"    Lightweight:    {lightweight:>10,}  (price history only)")
        self.stdout.write(f"    With price:     {with_price:>10,}")
        self.stdout.write(f"    With images:    {with_images:>10,}")
        self.stdout.write(f"    With rating:    {with_rating:>10,}")

        # Backfill pipeline counts
        total_bf = BackfillProduct.objects.count()
        bf_status = dict(
            BackfillProduct.objects.values_list("status")
            .annotate(c=Count("id"))
            .values_list("status", "c")
        )
        bf_scrape = dict(
            BackfillProduct.objects.values_list("scrape_status")
            .annotate(c=Count("id"))
            .values_list("scrape_status", "c")
        )
        bf_priority = dict(
            BackfillProduct.objects.filter(scrape_status="pending")
            .values_list("enrichment_priority")
            .annotate(c=Count("id"))
            .values_list("enrichment_priority", "c")
        )

        self.stdout.write(f"\n  BACKFILL PIPELINE ({total_bf:,} total):")
        for status in ["discovered", "bh_filling", "bh_filled", "ph_extending",
                        "ph_extended", "done", "failed", "skipped"]:
            count = bf_status.get(status, 0)
            pct = (count / total_bf * 100) if total_bf else 0
            self.stdout.write(f"    {status:<16} {count:>10,}  ({pct:.1f}%)")

        self.stdout.write(f"\n  ENRICHMENT STATUS:")
        for status in ["pending", "enriching", "scraped", "failed"]:
            count = bf_scrape.get(status, 0)
            self.stdout.write(f"    {status:<16} {count:>10,}")

        self.stdout.write(f"\n  ENRICHMENT QUEUE (pending by priority):")
        for p in [0, 1, 2, 3]:
            count = bf_priority.get(p, 0)
            label = {0: "P0 (on-demand)", 1: "P1 (Playwright)", 2: "P2 (curl_cffi)", 3: "P3 (curl_cffi-low)"}
            self.stdout.write(f"    {label.get(p, f'P{p}'):<20} {count:>10,}")

        # Meilisearch
        try:
            from apps.search.tasks import _get_client
            client = _get_client()
            index = client.index("products")
            stats = index.get_stats()
            self.stdout.write(f"\n  MEILISEARCH:")
            self.stdout.write(f"    Documents indexed:  {stats.number_of_documents:>10,}")
        except Exception as e:
            self.stdout.write(f"\n  MEILISEARCH: unavailable ({e})")

        # Launch readiness summary
        self.stdout.write("\n" + "-" * 70)
        self.stdout.write("  LAUNCH READINESS:")

        ready_items = []
        issues = []

        if with_price >= 50000:
            ready_items.append(f"  [OK] {with_price:,} products with price data")
        else:
            issues.append(f"  [!!] Only {with_price:,} products with price data (target: 50K+)")

        done = bf_status.get("done", 0) + bf_status.get("ph_extended", 0)
        if done >= 50000:
            ready_items.append(f"  [OK] {done:,} products with price history")
        else:
            issues.append(f"  [!!] Only {done:,} products with price history (target: 50K+)")

        if enriched >= 100:
            ready_items.append(f"  [OK] {enriched:,} fully enriched products")
        else:
            issues.append(f"  [!!] Only {enriched:,} fully enriched (need more for rich product pages)")

        failed = bf_status.get("failed", 0) + bf_scrape.get("failed", 0)
        if failed > 0:
            issues.append(f"  [!!] {failed:,} failed products — run `analyze-failed` to investigate")

        for item in ready_items:
            self.stdout.write(self.style.SUCCESS(item))
        for item in issues:
            self.stdout.write(self.style.WARNING(item))

        # Recommendations
        self.stdout.write("\n  RECOMMENDED ACTIONS:")
        if bf_priority.get(1, 0) == 0 and bf_priority.get(2, 0) == 0:
            self.stdout.write("    1. Run: python manage.py launch_prep prioritize --top 5000")
        pending_p1 = bf_priority.get(1, 0)
        if pending_p1 > 0:
            self.stdout.write(f"    2. Run: python manage.py launch_prep boost-enrich --batch 200 --rounds 25")
        if failed > 100:
            self.stdout.write(f"    3. Run: python manage.py launch_prep reset-retryable")
        try:
            from apps.search.tasks import _get_client
            client = _get_client()
            stats = client.index("products").get_stats()
            if stats.number_of_documents < with_price:
                self.stdout.write(f"    4. Run: python manage.py launch_prep sync-search")
        except Exception:
            pass

        self.stdout.write("=" * 70 + "\n")

    # ──────────────────────────────────────────────────────────────────
    # PRIORITIZE
    # ──────────────────────────────────────────────────────────────────

    def _prioritize(self, top_n: int, dry_run: bool):
        from apps.pricing.backfill.prioritizer import (
            assign_enrichment_priorities,
            assign_review_targets,
            populate_derived_fields,
        )
        from apps.pricing.models import BackfillProduct

        self.stdout.write(f"\nPrioritizing top {top_n:,} products for enrichment...\n")

        # Step 1: Populate derived fields (price, category from title)
        self.stdout.write("  Step 1: Populating derived fields (price, category)...")
        if not dry_run:
            result = populate_derived_fields()
            self.stdout.write(f"    Price filled: {result['price_filled']:,}")
            self.stdout.write(f"    Category filled: {result['category_filled']:,}")
        else:
            no_price = BackfillProduct.objects.filter(
                current_price__isnull=True
            ).exclude(raw_price_data=[]).count()
            no_cat = BackfillProduct.objects.filter(category_name="").exclude(title="").count()
            self.stdout.write(f"    Would fill price for ~{no_price:,} records")
            self.stdout.write(f"    Would fill category for ~{no_cat:,} records")

        # Step 2: Assign enrichment priorities
        self.stdout.write("\n  Step 2: Assigning enrichment priorities...")
        if not dry_run:
            result = assign_enrichment_priorities()
            self.stdout.write(f"    P1 (Playwright): {result['p1']:,}")
            self.stdout.write(f"    P2 (curl_cffi):  {result['p2']:,}")
        else:
            self.stdout.write("    [DRY RUN] Would assign P1/P2/P3 based on popularity + category")

        # Step 3: If we have too many P1+P2, cap to top_n
        if not dry_run:
            p1_count = BackfillProduct.objects.filter(
                scrape_status="pending", enrichment_priority=1
            ).count()
            p2_count = BackfillProduct.objects.filter(
                scrape_status="pending", enrichment_priority=2
            ).count()
            total_high = p1_count + p2_count

            self.stdout.write(f"\n  Current queue: P1={p1_count:,}, P2={p2_count:,} (total={total_high:,})")

            if total_high > top_n:
                # Demote excess P2 to P3 (keep all P1, trim P2)
                excess = total_high - top_n
                if excess > 0 and p2_count > 0:
                    demote_count = min(excess, p2_count)
                    # Demote least popular P2 products
                    demote_ids = list(
                        BackfillProduct.objects.filter(
                            scrape_status="pending", enrichment_priority=2
                        )
                        .order_by("price_data_points")
                        .values_list("id", flat=True)[:demote_count]
                    )
                    BackfillProduct.objects.filter(id__in=demote_ids).update(enrichment_priority=3)
                    self.stdout.write(f"    Demoted {demote_count:,} low-popularity P2 → P3 (capped to top {top_n:,})")

        # Step 4: Assign review targets
        self.stdout.write("\n  Step 3: Assigning review targets (top 100K)...")
        if not dry_run:
            review_count = assign_review_targets(max_review_products=min(top_n * 2, 100_000))
            self.stdout.write(f"    Review targets assigned: {review_count:,}")
        else:
            self.stdout.write("    [DRY RUN] Would assign review targets")

        # Final summary
        if not dry_run:
            dist = dict(
                BackfillProduct.objects.filter(scrape_status="pending")
                .values_list("enrichment_priority")
                .annotate(c=Count("id"))
                .values_list("enrichment_priority", "c")
            )
            self.stdout.write(f"\n  Final enrichment queue:")
            for p in [0, 1, 2, 3]:
                self.stdout.write(f"    P{p}: {dist.get(p, 0):,}")

            total_to_enrich = sum(dist.values())
            # Time estimates
            p1_time = dist.get(1, 0) * 30 / 3600  # ~30s per P1 product
            p2_time = dist.get(2, 0) * 2 / 3600   # ~2s per P2 product
            p3_time = dist.get(3, 0) * 2 / 3600   # ~2s per P3 product
            self.stdout.write(f"\n  Estimated enrichment time:")
            self.stdout.write(f"    P1: ~{p1_time:.1f} hours")
            self.stdout.write(f"    P2: ~{p2_time:.1f} hours")
            self.stdout.write(f"    P3: ~{p3_time:.1f} hours")
            self.stdout.write(f"    Total queue: {total_to_enrich:,} products")

        self.stdout.write(self.style.SUCCESS("\n  Done! Run `boost-enrich` to start processing.\n"))

    # ──────────────────────────────────────────────────────────────────
    # ANALYZE FAILED
    # ──────────────────────────────────────────────────────────────────

    def _analyze_failed(self, limit: int):
        from apps.pricing.models import BackfillProduct

        self.stdout.write("\n" + "=" * 70)
        self.stdout.write("  FAILURE ANALYSIS")
        self.stdout.write("=" * 70)

        # Pipeline failures (status=failed)
        pipeline_failed = BackfillProduct.objects.filter(status="failed").count()
        # Enrichment failures (scrape_status=failed)
        enrich_failed = BackfillProduct.objects.filter(scrape_status="failed").count()
        enrich_retryable = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__lt=3
        ).count()
        enrich_exhausted = BackfillProduct.objects.filter(
            scrape_status="failed", retry_count__gte=3
        ).count()
        # Review failures
        review_failed = BackfillProduct.objects.filter(review_status="failed").count()

        self.stdout.write(f"\n  Pipeline failures (status=failed):     {pipeline_failed:>8,}")
        self.stdout.write(f"  Enrichment failures (scrape=failed):   {enrich_failed:>8,}")
        self.stdout.write(f"    - Retryable (retry_count < 3):       {enrich_retryable:>8,}")
        self.stdout.write(f"    - Exhausted (retry_count >= 3):      {enrich_exhausted:>8,}")
        self.stdout.write(f"  Review failures (review=failed):       {review_failed:>8,}")

        # Error message patterns for pipeline failures
        if pipeline_failed > 0:
            self.stdout.write(f"\n  TOP PIPELINE FAILURE PATTERNS:")
            errors = (
                BackfillProduct.objects.filter(status="failed")
                .exclude(error_message="")
                .values_list("error_message", flat=True)[:limit]
            )
            patterns = Counter()
            for msg in errors:
                # Normalize: truncate to first 80 chars for grouping
                key = (msg or "empty")[:80]
                patterns[key] += 1

            for pattern, count in patterns.most_common(10):
                self.stdout.write(f"    [{count:>5}x] {pattern}")

            no_msg = BackfillProduct.objects.filter(
                status="failed", error_message=""
            ).count()
            if no_msg:
                self.stdout.write(f"    [{no_msg:>5}x] (no error message)")

        # Error patterns for enrichment failures
        if enrich_failed > 0:
            self.stdout.write(f"\n  TOP ENRICHMENT FAILURE PATTERNS:")
            errors = (
                BackfillProduct.objects.filter(scrape_status="failed")
                .exclude(error_message="")
                .values_list("error_message", flat=True)[:limit]
            )
            patterns = Counter()
            for msg in errors:
                key = (msg or "empty")[:80]
                patterns[key] += 1

            for pattern, count in patterns.most_common(10):
                self.stdout.write(f"    [{count:>5}x] {pattern}")

        # Failures by marketplace
        self.stdout.write(f"\n  FAILURES BY MARKETPLACE:")
        by_mp = (
            BackfillProduct.objects.filter(
                Q(status="failed") | Q(scrape_status="failed")
            )
            .values("marketplace_slug")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        for row in by_mp[:10]:
            self.stdout.write(f"    {row['marketplace_slug']:<20} {row['c']:>8,}")

        # Failures by category
        self.stdout.write(f"\n  FAILURES BY CATEGORY:")
        by_cat = (
            BackfillProduct.objects.filter(
                Q(status="failed") | Q(scrape_status="failed")
            )
            .values("category_name")
            .annotate(c=Count("id"))
            .order_by("-c")
        )
        for row in by_cat[:10]:
            cat = row["category_name"] or "(uncategorized)"
            self.stdout.write(f"    {cat:<20} {row['c']:>8,}")

        # Recommendations
        self.stdout.write(f"\n  RECOMMENDATIONS:")
        if enrich_retryable > 0:
            self.stdout.write(f"    - {enrich_retryable:,} retryable failures: run `reset-retryable --type enrichment`")
        if pipeline_failed > 0:
            self.stdout.write(f"    - {pipeline_failed:,} pipeline failures: run `reset-retryable --type pipeline`")
        if review_failed > 0:
            self.stdout.write(f"    - {review_failed:,} review failures: run `reset-retryable --type reviews`")

        self.stdout.write("=" * 70 + "\n")

    # ──────────────────────────────────────────────────────────────────
    # RESET RETRYABLE
    # ──────────────────────────────────────────────────────────────────

    def _reset_retryable(self, reset_all: bool, reset_type: str, dry_run: bool):
        from apps.pricing.models import BackfillProduct

        self.stdout.write("\nResetting failures...\n")

        if reset_type in ("pipeline", "all"):
            if reset_all:
                qs = BackfillProduct.objects.filter(status="failed")
            else:
                # Only reset those with retry_count < 3
                qs = BackfillProduct.objects.filter(status="failed", retry_count__lt=3)

            count = qs.count()
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would reset {count:,} pipeline failures → discovered")
            elif count > 0:
                qs.update(status="discovered", retry_count=0, error_message="")
                self.stdout.write(self.style.SUCCESS(f"  Reset {count:,} pipeline failures → discovered"))
            else:
                self.stdout.write("  No pipeline failures to reset")

        if reset_type in ("enrichment", "all"):
            if reset_all:
                qs = BackfillProduct.objects.filter(scrape_status="failed")
            else:
                qs = BackfillProduct.objects.filter(scrape_status="failed", retry_count__lt=3)

            count = qs.count()
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would reset {count:,} enrichment failures → pending")
            elif count > 0:
                qs.update(scrape_status="pending", retry_count=0, error_message="")
                self.stdout.write(self.style.SUCCESS(f"  Reset {count:,} enrichment failures → pending"))
            else:
                self.stdout.write("  No enrichment failures to reset")

        if reset_type in ("reviews", "all"):
            qs = BackfillProduct.objects.filter(review_status="failed")
            count = qs.count()
            if dry_run:
                self.stdout.write(f"  [DRY RUN] Would reset {count:,} review failures → pending")
            elif count > 0:
                qs.update(review_status="pending", error_message="")
                self.stdout.write(self.style.SUCCESS(f"  Reset {count:,} review failures → pending"))
            else:
                self.stdout.write("  No review failures to reset")

        self.stdout.write("")

    # ──────────────────────────────────────────────────────────────────
    # BOOST ENRICH
    # ──────────────────────────────────────────────────────────────────

    def _boost_enrich(self, batch_size: int, rounds: int, delay: int, priority: int | None):
        from apps.pricing.backfill.enrichment import enrich_single_product
        from apps.pricing.models import BackfillProduct

        self.stdout.write(f"\nBoost enrichment: {rounds} rounds × {batch_size} products")
        self.stdout.write(f"  Delay between rounds: {delay}s")
        if priority is not None:
            self.stdout.write(f"  Filtering to priority: P{priority}")
        self.stdout.write("")

        total_dispatched = 0

        for i in range(1, rounds + 1):
            qs = BackfillProduct.objects.filter(
                scrape_status="pending",
            ).exclude(marketplace_url="")

            if priority is not None:
                qs = qs.filter(enrichment_priority=priority)

            product_ids = list(
                qs.order_by("enrichment_priority", "created_at")
                .values_list("id", flat=True)[:batch_size]
            )

            if not product_ids:
                self.stdout.write(f"  Round {i}: No more pending products. Stopping.")
                break

            for bp_id in product_ids:
                enrich_single_product.delay(str(bp_id))

            total_dispatched += len(product_ids)
            self.stdout.write(
                f"  Round {i}/{rounds}: dispatched {len(product_ids)} tasks "
                f"(total: {total_dispatched:,})"
            )

            if i < rounds:
                time.sleep(delay)

        self.stdout.write(self.style.SUCCESS(
            f"\n  Total dispatched: {total_dispatched:,} enrichment tasks\n"
        ))

    # ──────────────────────────────────────────────────────────────────
    # SYNC SEARCH
    # ──────────────────────────────────────────────────────────────────

    def _sync_search(self, lightweight_only: bool):
        from apps.products.models import Product
        from apps.search.tasks import _configure_index, _get_client, _product_to_document

        self.stdout.write("\nSyncing products to Meilisearch...\n")

        try:
            client = _get_client()
        except (ImportError, ValueError) as e:
            self.stdout.write(self.style.ERROR(f"  Meilisearch unavailable: {e}"))
            return

        index = client.index("products")

        # Configure index settings
        self.stdout.write("  Configuring index settings...")
        _configure_index(index)

        # Build queryset
        qs = Product.objects.select_related(
            "brand", "category__parent__parent"
        ).filter(status="active")

        if lightweight_only:
            qs = qs.filter(is_lightweight=True)
            self.stdout.write("  Filtering to lightweight products only")

        total = qs.count()
        self.stdout.write(f"  Products to sync: {total:,}")

        synced = 0
        errors = 0
        batch_size = 500

        for offset in range(0, total, batch_size):
            batch = qs[offset:offset + batch_size]
            documents = [_product_to_document(p) for p in batch]

            try:
                task_info = index.add_documents(documents, primary_key="id")
                client.wait_for_task(task_info.task_uid, timeout_in_ms=120_000)
                synced += len(documents)
            except Exception as e:
                logger.exception("Meilisearch batch failed at offset %d", offset)
                errors += len(documents)

            if (offset + batch_size) % 5000 == 0 or offset + batch_size >= total:
                self.stdout.write(f"  Progress: {min(offset + batch_size, total):,}/{total:,} ({synced:,} synced, {errors} errors)")

        # Final stats
        stats = index.get_stats()
        self.stdout.write(self.style.SUCCESS(
            f"\n  Done! Synced: {synced:,}, Errors: {errors}"
        ))
        self.stdout.write(f"  Total documents in index: {stats.number_of_documents:,}\n")
