"""Celery tasks for launching and managing scraping jobs.

All tasks run on the ``scraping`` queue.  Spiders are executed in a
subprocess via ``apps.scraping.runner`` to avoid Twisted reactor restart
issues inside Celery workers.
"""
import logging
import os
import subprocess
import sys

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUNNER_MODULE = "apps.scraping.runner"


# ---------------------------------------------------------------------------
# Primary task — run a marketplace spider (Beat entry point)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping", bind=True, max_retries=1, default_retry_delay=600)
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
    timeout = ScrapingConfig.spider_timeout()
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
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BACKEND_DIR,
            timeout=timeout,
            env=env,
        )

        job.finished_at = timezone.now()

        if result.returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
            logger.info("Spider %s completed for %s", spider_name, marketplace_slug)
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = (result.stderr or result.stdout or "")[:2000]
            logger.error("Spider %s failed: %s", spider_name, job.error_message[:200])

    except subprocess.TimeoutExpired:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = f"Spider timed out after {timeout}s"
        logger.error("Spider %s timed out for %s", spider_name, marketplace_slug)

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

    return {
        "success": job.status == ScraperJob.Status.COMPLETED,
        "job_id": str(job.id),
        "status": job.status,
        "marketplace": marketplace_slug,
        "spider": spider_name,
    }


# ---------------------------------------------------------------------------
# Lower-level spider runner (for direct invocation / ad-hoc jobs)
# ---------------------------------------------------------------------------

@shared_task(queue="scraping", bind=True, max_retries=1, default_retry_delay=300)
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
    timeout = ScrapingConfig.spider_timeout()
    cmd = [
        sys.executable, "-m", RUNNER_MODULE,
        spider_name,
        "--job-id", str(job.id),
    ]

    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=BACKEND_DIR,
            timeout=timeout,
            env=env,
        )

        job.finished_at = timezone.now()

        if result.returncode == 0:
            job.status = ScraperJob.Status.COMPLETED
            logger.info("Spider %s completed for %s", spider_name, marketplace_slug)
        else:
            job.status = ScraperJob.Status.FAILED
            job.error_message = (result.stderr or result.stdout or "")[:2000]
            logger.error("Spider %s failed: %s", spider_name, job.error_message[:200])

    except subprocess.TimeoutExpired:
        job.finished_at = timezone.now()
        job.status = ScraperJob.Status.FAILED
        job.error_message = f"Spider timed out after {timeout}s"
        logger.error("Spider %s timed out for %s", spider_name, marketplace_slug)

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
