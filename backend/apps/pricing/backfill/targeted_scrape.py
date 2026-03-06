"""Targeted scraping: BackfillProduct ASINs/FPIDs → Spider → ProductListing.

Reads products from BackfillProduct that have price data cached but no
matching ProductListing, constructs direct product URLs, and launches
marketplace spiders to scrape their detail pages.

After each spider batch, a reconciliation step checks which products
got ProductListings and updates scrape_status accordingly.

Usage::

    python manage.py backfill_prices scrape --marketplace amazon-in --limit 50
    python manage.py backfill_prices scrape --dry-run
"""
from __future__ import annotations

import logging
import os
import sys

from django.db.models import Case, When

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
RUNNER_MODULE = "apps.scraping.runner"


def scrape_backfill_products(
    batch_size: int | None = None,
    marketplace_slug: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
    include_retried: bool = False,
    auto_inject: bool = False,
) -> dict:
    """Launch spiders to scrape BackfillProduct ASINs/FPIDs.

    Args:
        batch_size: URLs per spider subprocess (default from config).
        marketplace_slug: Filter by marketplace slug.
        limit: Max total products to scrape.
        dry_run: Show what would be scraped without launching spiders.
        include_retried: Include products with retry_count >= max_retries.
        auto_inject: Run Phase 4 inject after scraping completes.

    Returns:
        Stats dict with counts.
    """
    from common.app_settings import ScrapingConfig

    batch_size = batch_size or BackfillConfig.scrape_batch_size()
    max_retries = BackfillConfig.scrape_max_retries()
    url_map = BackfillConfig.product_url_map()
    spider_map = ScrapingConfig.spider_map()

    # Only marketplaces with both a spider AND a URL template
    supported = set(url_map.keys()) & set(spider_map.keys())

    # Query candidates
    qs = BackfillProduct.objects.filter(
        status__in=[
            BackfillProduct.Status.BH_FILLED,
            BackfillProduct.Status.PH_EXTENDED,
        ],
        scrape_status__in=["pending", "failed"],
        product_listing__isnull=True,
    ).exclude(external_id="")

    if not include_retried:
        qs = qs.exclude(scrape_status="failed", retry_count__gte=max_retries)

    if marketplace_slug:
        qs = qs.filter(marketplace_slug=marketplace_slug)
    else:
        qs = qs.filter(marketplace_slug__in=supported)

    # Pending first, then failed with lowest retry count
    qs = qs.order_by(
        Case(When(scrape_status="pending", then=0), default=1),
        "retry_count",
        "created_at",
    )

    if limit:
        qs = qs[:limit]

    candidates = list(qs)
    total = len(candidates)

    if total == 0:
        logger.info("Targeted scrape: no candidates found")
        return {
            "total": 0, "batches": 0, "scraped": 0,
            "failed": 0, "skipped_marketplace": 0,
        }

    # Group by marketplace
    by_marketplace: dict[str, list[BackfillProduct]] = {}
    skipped = 0
    for bp in candidates:
        if bp.marketplace_slug not in supported:
            skipped += 1
            continue
        by_marketplace.setdefault(bp.marketplace_slug, []).append(bp)

    if skipped:
        logger.warning(
            "Targeted scrape: %d products skipped (no spider/URL template)", skipped
        )

    stats = {
        "total": total,
        "batches": 0,
        "scraped": 0,
        "failed": 0,
        "skipped_marketplace": skipped,
    }

    if dry_run:
        for slug, bps in by_marketplace.items():
            batch_count = (len(bps) + batch_size - 1) // batch_size
            logger.info(
                "  [DRY RUN] %s: %d products → %d batches of %d",
                slug, len(bps), batch_count, batch_size,
            )
            # Show first 5 URLs as preview
            template = url_map[slug]
            for bp in bps[:5]:
                logger.info("    %s", template.format(pid=bp.external_id))
            if len(bps) > 5:
                logger.info("    ... and %d more", len(bps) - 5)
        stats["batches"] = sum(
            (len(bps) + batch_size - 1) // batch_size
            for bps in by_marketplace.values()
        )
        return stats

    # Launch spider batches per marketplace
    for slug, bps in by_marketplace.items():
        spider_name = spider_map[slug]
        template = url_map[slug]

        for i in range(0, len(bps), batch_size):
            batch_bps = bps[i : i + batch_size]
            batch_urls = [template.format(pid=bp.external_id) for bp in batch_bps]
            stats["batches"] += 1

            logger.info(
                "Targeted scrape batch %d: %s — %d URLs",
                stats["batches"], slug, len(batch_urls),
            )

            # Launch spider subprocess
            success = _run_spider_batch(spider_name, batch_urls, slug)

            # Reconcile: check which products got ProductListings
            matched = _reconcile_batch(batch_bps, slug)
            stats["scraped"] += matched
            stats["failed"] += len(batch_bps) - matched

            logger.info(
                "  Batch %d result: %d scraped, %d failed (spider %s)",
                stats["batches"], matched, len(batch_bps) - matched,
                "ok" if success else "error",
            )

    logger.info("Targeted scrape complete: %s", stats)

    # Chain Phase 4 inject if requested
    if auto_inject and stats["scraped"] > 0:
        from apps.pricing.backfill.phase4_inject import inject_cached_data
        inject_result = inject_cached_data(marketplace_slug=marketplace_slug)
        logger.info("Auto-inject after scrape: %s", inject_result)
        stats["inject"] = inject_result

    return stats


def _run_spider_batch(spider_name: str, urls: list[str], marketplace_slug: str) -> bool:
    """Launch a spider subprocess for a batch of product URLs.

    Returns True if spider exited successfully.
    """
    import subprocess

    from apps.scraping.models import ScraperJob
    from apps.products.models import Marketplace

    # Create ScraperJob for tracking
    marketplace = Marketplace.objects.get(slug=marketplace_slug)
    job = ScraperJob.objects.create(
        marketplace=marketplace,
        spider_name=spider_name,
        triggered_by="backfill",
    )

    from django.utils import timezone
    job.status = ScraperJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--job-id", str(job.id),
        "--urls", ",".join(urls),
        "--max-pages", "1",
    ]

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        from apps.scraping.tasks import _run_spider_process
        returncode, tail_output = _run_spider_process(cmd, env, spider_name)

        job.finished_at = timezone.now()
        if returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = tail_output[:2000]
        job.save(update_fields=["status", "finished_at", "error_message"])
        return returncode == 0

    except Exception as exc:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        job.save(update_fields=["status", "finished_at", "error_message"])
        logger.exception("Spider %s raised an exception", spider_name)
        return False


def _reconcile_batch(
    batch_bps: list[BackfillProduct], marketplace_slug: str
) -> int:
    """Check which products got ProductListings after spider ran.

    Returns count of successfully matched products.
    """
    from apps.products.models import ProductListing

    external_ids = [bp.external_id for bp in batch_bps]
    created_listings = dict(
        ProductListing.objects.filter(
            marketplace__slug=marketplace_slug,
            external_id__in=external_ids,
        ).values_list("external_id", "id")
    )

    matched = 0
    for bp in batch_bps:
        listing_id = created_listings.get(bp.external_id)
        if listing_id:
            bp.product_listing_id = listing_id
            bp.scrape_status = BackfillProduct.ScrapeStatus.SCRAPED
            bp.save(update_fields=["product_listing_id", "scrape_status", "updated_at"])
            matched += 1
        else:
            bp.scrape_status = BackfillProduct.ScrapeStatus.FAILED
            bp.retry_count += 1
            bp.error_message = f"scrape: no listing created (attempt {bp.retry_count})"
            bp.save(update_fields=[
                "scrape_status", "retry_count", "error_message", "updated_at"
            ])

    return matched
