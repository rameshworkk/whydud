"""Celery tasks for launching and managing scraping jobs.

All tasks run on the ``scraping`` queue.  Spiders are executed in a
subprocess via ``apps.scraping.runner`` to avoid Twisted reactor restart
issues inside Celery workers.
"""
import collections
import logging
import os
import subprocess
import sys
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER_MODULE = "apps.scraping.runner"

# Number of trailing output lines to keep for error reporting
_TAIL_LINES = 80


def _run_spider_process(cmd: list[str], env: dict, spider_name: str) -> tuple[int, str]:
    """Run a spider subprocess, streaming output to the celery worker log.

    Returns (returncode, last_output) where last_output is the tail of
    stderr+stdout for error reporting.  No timeout — spiders run to completion.
    """
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        cwd=BACKEND_DIR,
        env=env,
    )
    tail = collections.deque(maxlen=_TAIL_LINES)
    for line in proc.stdout:
        line = line.rstrip()
        tail.append(line)
        logger.info("[%s] %s", spider_name, line)
    proc.wait()
    return proc.returncode, "\n".join(tail)


# ---------------------------------------------------------------------------
# Primary task — run a marketplace spider (Beat entry point)
# ---------------------------------------------------------------------------

@shared_task(
    queue="scraping",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    soft_time_limit=None,   # no limit — scraping can take hours
    time_limit=None,        # no limit
)
def run_marketplace_spider(self, marketplace_slug: str, category_slugs: list[str] | None = None) -> dict:
    """Run a specific marketplace spider with full orchestration.

    This is the primary Celery Beat entry point.  Resolves the spider name
    from the marketplace slug via ``ScrapingConfig.spider_map()``, creates a
    ``ScraperJob`` for tracking, launches the spider as a subprocess, and
    triggers downstream tasks on success:
      - ``sync_products_to_meilisearch`` (search index refresh)
      - ``check_price_alerts`` (notify users whose target price was hit)

    Args:
        marketplace_slug: e.g. ``"amazon-in"`` or ``"flipkart"``.
        category_slugs: Optional list of category URLs to scrape.
            When *None* the spider uses its built-in seed URLs.

    Beat schedule (registered in ``whydud/celery.py``):
      - ``amazon-in``: every 6 h at 00:00, 06:00, 12:00, 18:00 UTC
      - ``flipkart``:  every 6 h at 03:00, 09:00, 15:00, 21:00 UTC
    """
    from apps.scraping.models import ScraperJob
    from apps.products.models import Marketplace
    from common.app_settings import ScrapingConfig

    # Resolve spider name from marketplace slug
    spider_map = ScrapingConfig.spider_map()
    spider_name = spider_map.get(marketplace_slug)
    if not spider_name:
        logger.error("No spider configured for marketplace '%s'", marketplace_slug)
        return {"success": False, "error": f"No spider for marketplace: {marketplace_slug}"}

    # Validate marketplace exists in DB
    try:
        marketplace = Marketplace.objects.get(slug=marketplace_slug)
    except Marketplace.DoesNotExist:
        logger.error("Marketplace '%s' not found in DB", marketplace_slug)
        return {"success": False, "error": f"Unknown marketplace: {marketplace_slug}"}

    # Create ScraperJob record
    job = ScraperJob.objects.create(
        marketplace=marketplace,
        spider_name=spider_name,
        triggered_by="scheduled",
    )
    job.status = ScraperJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    # Build subprocess command
    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--job-id", str(job.id),
    ]
    if category_slugs:
        cmd.extend(["--urls", ",".join(category_slugs)])

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        returncode, tail_output = _run_spider_process(cmd, env, spider_name)

        job.finished_at = timezone.now()

        if returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
            logger.info("Spider %s completed for %s", spider_name, marketplace_slug)
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = tail_output[:2000]
            logger.error("Spider %s failed: %s", spider_name, job.error_message[:200])

    except Exception as exc:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        logger.exception("Spider %s raised an exception", spider_name)

    job.save(update_fields=["status", "finished_at", "error_message"])

    # Trigger downstream tasks on success
    if job.status == ScraperJob.Status.COMPLETED:
        from apps.search.tasks import sync_products_to_meilisearch
        from apps.pricing.tasks import check_price_alerts

        sync_products_to_meilisearch.delay()
        logger.info("Queued Meilisearch sync after %s spider completed", spider_name)

        check_price_alerts.delay()
        logger.info("Queued price alert check after %s spider completed", spider_name)

        # Chain review spider after successful product scrape
        review_spider = ScrapingConfig.review_spider_map().get(marketplace_slug)
        if review_spider:
            run_review_spider.delay(marketplace_slug)
            logger.info("Queued review spider %s after %s completed", review_spider, spider_name)

    return {
        "success": job.status == ScraperJob.Status.COMPLETED,
        "job_id": str(job.id),
        "status": job.status,
        "marketplace": marketplace_slug,
        "spider": spider_name,
    }


# ---------------------------------------------------------------------------
# Review spider — scrape reviews for products after product scrape
# ---------------------------------------------------------------------------

@shared_task(
    queue="scraping",
    bind=True,
    max_retries=1,
    default_retry_delay=600,
    soft_time_limit=None,   # no limit — scraping can take hours
    time_limit=None,        # no limit
)
def run_review_spider(
    self,
    marketplace_slug: str,
    max_review_pages: int | None = None,
    product_external_ids: list[str] | None = None,
) -> dict:
    """Scrape reviews for products from a marketplace.

    Triggered automatically after a successful product spider run (chained
    from ``run_marketplace_spider``) and also scheduled independently via
    Celery Beat for daily catch-up.

    When ``product_external_ids`` is provided (by the enrichment pipeline),
    the spider only scrapes reviews for those specific products instead of
    its default batch.

    The review spiders handle dedup internally (skip existing
    ``external_review_id``), so double-running is safe.

    After completion, queues ``detect_fake_reviews`` and
    ``compute_dudscore`` for products that received new reviews.
    """
    from apps.scraping.models import ScraperJob
    from apps.products.models import Marketplace
    from common.app_settings import ScrapingConfig

    # Resolve review spider name
    review_spider_map = ScrapingConfig.review_spider_map()
    spider_name = review_spider_map.get(marketplace_slug)
    if not spider_name:
        logger.error("No review spider for marketplace '%s'", marketplace_slug)
        return {"success": False, "error": f"No review spider for: {marketplace_slug}"}

    if max_review_pages is None:
        max_review_pages = ScrapingConfig.default_max_review_pages()

    # Validate marketplace
    try:
        marketplace = Marketplace.objects.get(slug=marketplace_slug)
    except Marketplace.DoesNotExist:
        logger.error("Marketplace '%s' not found in DB", marketplace_slug)
        return {"success": False, "error": f"Unknown marketplace: {marketplace_slug}"}

    # Create ScraperJob for tracking
    job = ScraperJob.objects.create(
        marketplace=marketplace,
        spider_name=spider_name,
        triggered_by="scheduled",
    )
    job.status = ScraperJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    # Build subprocess command
    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--job-id", str(job.id),
        "--max-review-pages", str(max_review_pages),
    ]
    if product_external_ids:
        cmd.extend(["--external-ids", ",".join(product_external_ids)])

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        returncode, tail_output = _run_spider_process(cmd, env, spider_name)

        job.finished_at = timezone.now()

        if returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
            logger.info("Review spider %s completed for %s", spider_name, marketplace_slug)
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = tail_output[:2000]
            logger.error("Review spider %s failed: %s", spider_name, job.error_message[:200])

    except Exception as exc:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        logger.exception("Review spider %s raised an exception", spider_name)

    job.save(update_fields=["status", "finished_at", "error_message"])

    # Trigger downstream tasks on success
    products_processed = 0
    if job.status == ScraperJob.Status.COMPLETED:
        products_processed = _queue_review_downstream_tasks(marketplace_slug)

    return {
        "success": job.status == ScraperJob.Status.COMPLETED,
        "job_id": str(job.id),
        "status": job.status,
        "marketplace": marketplace_slug,
        "spider": spider_name,
        "products_with_new_reviews": products_processed,
        "fraud_detection_run": products_processed > 0,
        "dudscore_recalc_queued": products_processed > 0,
    }


def _queue_review_downstream_tasks(marketplace_slug: str) -> int:
    """Run post-review-scrape processing for products that got new reviews.

    1. Fraud detection (Celery task per product)
    2. DudScore recalculation (Celery task per product)
    3. Update product aggregate review stats (avg_rating, total_reviews)

    Returns the number of products processed.
    """
    from apps.products.models import Product
    from apps.reviews.models import Review
    from apps.reviews.tasks import detect_fake_reviews
    from apps.scoring.tasks import compute_dudscore
    from django.db.models import Avg, Count

    # Find products that got new reviews in the last 2 hours (covers the scrape window)
    cutoff = timezone.now() - timedelta(hours=2)
    product_ids = list(
        Review.objects
        .filter(
            marketplace__slug=marketplace_slug,
            created_at__gte=cutoff,
        )
        .values_list("product_id", flat=True)
        .distinct()
    )

    for pid in product_ids:
        # 1. Fraud detection
        detect_fake_reviews.delay(str(pid))

        # 2. DudScore recalc
        compute_dudscore.delay(str(pid))

        # 3. Update aggregate review stats on the product
        try:
            product = Product.objects.get(id=pid)
            stats = product.reviews.filter(is_published=True).aggregate(
                avg_rating=Avg("rating"),
                total_reviews=Count("id"),
            )
            product.avg_rating = stats["avg_rating"] or 0
            product.total_reviews = stats["total_reviews"] or 0
            product.save(update_fields=["avg_rating", "total_reviews"])
        except Product.DoesNotExist:
            logger.warning("Product %s not found during review stats update", pid)

    logger.info(
        "Post-review processing for %d products (%s): "
        "fraud detection queued, DudScore recalc queued, review stats updated",
        len(product_ids),
        marketplace_slug,
    )
    return len(product_ids)


# ---------------------------------------------------------------------------
# Lower-level spider runner (for direct invocation / ad-hoc jobs)
# ---------------------------------------------------------------------------

@shared_task(
    queue="scraping",
    bind=True,
    max_retries=1,
    default_retry_delay=300,
    soft_time_limit=None,   # no limit — scraping can take hours
    time_limit=None,        # no limit
)
def run_spider(self, marketplace_slug: str, spider_name: str, job_id: str | None = None) -> dict:
    """Launch a Scrapy spider as a subprocess for a marketplace.

    Lower-level task used by ``scrape_daily_prices`` and direct invocations.
    Prefer ``run_marketplace_spider`` for Beat-scheduled runs.

    Creates/updates a ScraperJob row to track progress. Returns a summary dict.
    """
    from apps.scraping.models import ScraperJob
    from apps.products.models import Marketplace
    from common.app_settings import ScrapingConfig

    # Validate marketplace
    try:
        marketplace = Marketplace.objects.get(slug=marketplace_slug)
    except Marketplace.DoesNotExist:
        logger.error("Marketplace '%s' not found", marketplace_slug)
        return {"success": False, "error": f"Unknown marketplace: {marketplace_slug}"}

    # Create or fetch ScraperJob
    if job_id:
        try:
            job = ScraperJob.objects.get(id=job_id)
        except ScraperJob.DoesNotExist:
            job = ScraperJob.objects.create(
                marketplace=marketplace,
                spider_name=spider_name,
                triggered_by="scheduled",
            )
    else:
        job = ScraperJob.objects.create(
            marketplace=marketplace,
            spider_name=spider_name,
            triggered_by="scheduled",
        )

    # Mark as running
    job.status = ScraperJob.Status.RUNNING
    job.started_at = timezone.now()
    job.save(update_fields=["status", "started_at"])

    # Build subprocess command
    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--job-id", str(job.id),
    ]

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        returncode, tail_output = _run_spider_process(cmd, env, spider_name)

        job.finished_at = timezone.now()

        if returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
            logger.info("Spider %s completed for %s", spider_name, marketplace_slug)
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = tail_output[:2000]
            logger.error("Spider %s failed: %s", spider_name, job.error_message[:200])

    except Exception as exc:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = str(exc)[:2000]
        logger.exception("Spider %s raised an exception", spider_name)

    job.save(update_fields=["status", "finished_at", "error_message"])

    # Sync updated products to Meilisearch after a successful spider run
    if job.status == ScraperJob.Status.COMPLETED:
        from apps.search.tasks import sync_products_to_meilisearch
        sync_products_to_meilisearch.delay()
        logger.info("Queued Meilisearch sync after %s spider completed", spider_name)

    return {
        "success": job.status == ScraperJob.Status.COMPLETED,
        "job_id": str(job.id),
        "status": job.status,
        "marketplace": marketplace_slug,
        "spider": spider_name,
    }


# ---------------------------------------------------------------------------
# Ad-hoc single product scrape
# ---------------------------------------------------------------------------

@shared_task(queue="scraping")
def scrape_product_adhoc(url: str, marketplace_slug: str) -> dict:
    """On-demand scrape of a single product URL (e.g., triggered by user search).

    Runs the appropriate spider with the URL as a start URL.
    """
    from apps.products.models import Marketplace
    from common.app_settings import ScrapingConfig

    try:
        Marketplace.objects.get(slug=marketplace_slug)
    except Marketplace.DoesNotExist:
        return {"success": False, "error": f"Unknown marketplace: {marketplace_slug}"}

    # Determine spider from marketplace
    spider_name = ScrapingConfig.spider_map().get(marketplace_slug)
    if not spider_name:
        return {"success": False, "error": f"No spider for marketplace: {marketplace_slug}"}

    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--urls", url,
        "--max-pages", "1",
    ]

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BACKEND_DIR,
            timeout=120,  # single product: 2 min timeout
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "url": url,
            "marketplace": marketplace_slug,
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Scrape timed out"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


# ---------------------------------------------------------------------------
# Daily price scrape — runs all active marketplace spiders
# ---------------------------------------------------------------------------

@shared_task(queue="scraping")
def scrape_daily_prices() -> dict:
    """Launch spiders for all active marketplaces to refresh prices.

    Registered in Celery Beat for daily execution.
    """
    from apps.products.models import Marketplace
    from common.app_settings import ScrapingConfig

    spider_map = ScrapingConfig.spider_map()

    results: list[dict] = []
    active_marketplaces = Marketplace.objects.filter(scraper_status="active")

    for marketplace in active_marketplaces:
        spider_name = spider_map.get(marketplace.slug)
        if not spider_name:
            logger.info(f"No spider for {marketplace.slug} — skipping")
            continue

        logger.info(f"Queueing spider {spider_name} for {marketplace.slug}")
        # Chain into individual run_spider tasks (parallel execution)
        task_result = run_spider.delay(marketplace.slug, spider_name)
        results.append({
            "marketplace": marketplace.slug,
            "spider": spider_name,
            "task_id": str(task_result.id),
        })

    return {
        "spiders_launched": len(results),
        "details": results,
    }
