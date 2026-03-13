"""Celery application configuration for Whydud."""
import logging
import os

from celery import Celery
from celery.schedules import crontab
from celery.signals import setup_logging, task_failure, task_retry, task_success

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

# ---------------------------------------------------------------------------
# Sentry — Celery integration (piggybacks on Django init from settings)
# ---------------------------------------------------------------------------

if os.environ.get("SENTRY_DSN"):
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=os.environ["SENTRY_DSN"],
        integrations=[CeleryIntegration(monitor_beat_tasks=True)],
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        environment=os.environ.get("DJANGO_ENV", "development"),
        send_default_pii=False,
    )

app = Celery("whydud")

# Load config from Django settings, using CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all installed apps.
app.autodiscover_tasks()


# ---------------------------------------------------------------------------
# Colorized logging for Celery workers
# ---------------------------------------------------------------------------

@setup_logging.connect
def _setup_celery_logging(loglevel=None, logfile=None, format=None, colorize=None, **kwargs):
    """Install colorized formatter on Celery worker loggers.

    By connecting to ``setup_logging``, we prevent Celery from hijacking
    the root logger and instead install our own colored formatter.
    """
    from apps.pricing.backfill.log_colors import BackfillColorFormatter

    # Celery default format but with our color processor
    fmt = "[%(asctime)s: %(levelname)s/%(processName)s] %(message)s"
    formatter = BackfillColorFormatter(fmt)

    # Configure root logger
    root = logging.getLogger()
    root.setLevel(loglevel or logging.INFO)

    # File handler (no colors)
    if logfile:
        file_handler = logging.FileHandler(logfile)
        file_handler.setFormatter(logging.Formatter(fmt))
        root.addHandler(file_handler)

    # Console handler (with colors)
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    root.addHandler(console)


# Queue definitions
app.conf.task_queues = {
    "default": {"exchange": "default", "routing_key": "default"},
    "scraping": {"exchange": "scraping", "routing_key": "scraping"},
    "email": {"exchange": "email", "routing_key": "email"},
    "scoring": {"exchange": "scoring", "routing_key": "scoring"},
    "alerts": {"exchange": "alerts", "routing_key": "alerts"},
}
app.conf.task_default_queue = "default"

# Beat schedule (populated per sprint)
app.conf.beat_schedule = {
    "publish-pending-reviews-hourly": {
        "task": "apps.reviews.tasks.publish_pending_reviews",
        "schedule": crontab(minute=0),  # every hour at :00
    },
    "update-reviewer-profiles-weekly": {
        "task": "apps.reviews.tasks.update_reviewer_profiles",
        "schedule": crontab(minute=0, hour=0, day_of_week="monday"),  # Monday 00:00 UTC
    },
    "check-price-alerts-4h": {
        "task": "apps.pricing.tasks.check_price_alerts",
        "schedule": crontab(minute=0, hour="*/4"),  # every 4 hours at :00
    },
    "scrape-amazon-in-6h": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour="0,6,12,18"),  # every 6h at 00/06/12/18 UTC
        "args": ["amazon-in"],
        "options": {"queue": "scraping"},
    },
    "scrape-flipkart-6h": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour="3,9,15,21"),  # every 6h offset +3h from Amazon
        "args": ["flipkart"],
        "options": {"queue": "scraping"},
    },
    "meilisearch-full-reindex-daily": {
        "task": "apps.search.tasks.full_reindex",
        "schedule": crontab(minute=0, hour=1),  # daily at 01:00 UTC
    },
    "dudscore-full-recalc-monthly": {
        "task": "apps.scoring.tasks.full_dudscore_recalculation",
        "schedule": crontab(minute=0, hour=3, day_of_month=1),  # 1st of month, 03:00 UTC
    },
    "detect-deals-30m": {
        "task": "apps.deals.tasks.detect_blockbuster_deals",
        "schedule": crontab(minute="0,30"),  # every 30 minutes
        "options": {"queue": "scoring"},
    },
    # Independent daily review scrapes (catch-up, supplements chain from product spider)
    "scrape-amazon-in-reviews-daily": {
        "task": "apps.scraping.tasks.run_review_spider",
        "schedule": crontab(minute=0, hour=4),  # 04:00 UTC, after product scrapes
        "args": ["amazon-in"],
        "kwargs": {"max_review_pages": 3},
        "options": {"queue": "scraping"},
    },
    "scrape-flipkart-reviews-daily": {
        "task": "apps.scraping.tasks.run_review_spider",
        "schedule": crontab(minute=0, hour=7),  # 07:00 UTC
        "args": ["flipkart"],
        "kwargs": {"max_review_pages": 3},
        "options": {"queue": "scraping"},
    },
    # --- Daily scrapes for remaining 10 marketplaces (staggered across 24h) ---
    # Batch 1: Electronics sites (lower anti-bot, run early)
    "scrape-croma-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=8),  # 08:00 UTC (13:30 IST)
        "args": ["croma"],
        "options": {"queue": "scraping"},
    },
    "scrape-reliance-digital-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=30, hour=4),  # 04:30 UTC (10:00 IST)
        "args": ["reliance-digital"],
        "options": {"queue": "scraping"},
    },
    "scrape-vijay-sales-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=5),  # 05:00 UTC (10:30 IST)
        "args": ["vijay-sales"],
        "options": {"queue": "scraping"},
    },
    # Batch 2: Multi-category / beauty (medium anti-bot)
    "scrape-snapdeal-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=30, hour=7),  # 07:30 UTC (13:00 IST)
        "args": ["snapdeal"],
        "options": {"queue": "scraping"},
    },
    "scrape-nykaa-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=30, hour=8),  # 08:30 UTC (14:00 IST)
        "args": ["nykaa"],
        "options": {"queue": "scraping"},
    },
    # Batch 3: SPA sites with high anti-bot (run during off-peak hours)
    "scrape-tata-cliq-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=30, hour=6),  # 06:30 UTC (12:00 IST)
        "args": ["tata-cliq"],
        "options": {"queue": "scraping"},
    },
    "scrape-jiomart-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=13),  # 13:00 UTC (18:30 IST)
        "args": ["jiomart"],
        "options": {"queue": "scraping"},
    },
    "scrape-myntra-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=16),  # 16:00 UTC (21:30 IST)
        "args": ["myntra"],
        "options": {"queue": "scraping"},
    },
    "scrape-ajio-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=19),  # 19:00 UTC (00:30 IST next day)
        "args": ["ajio"],
        "options": {"queue": "scraping"},
    },
    "scrape-meesho-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=0, hour=10),  # 10:00 UTC (15:30 IST)
        "args": ["meesho"],
        "options": {"queue": "scraping"},
    },
    "scrape-firstcry-daily": {
        "task": "apps.scraping.tasks.run_marketplace_spider",
        "schedule": crontab(minute=30, hour=9),  # 09:30 UTC (15:00 IST)
        "args": ["firstcry"],
        "options": {"queue": "scraping"},
    },
    # --- Backfill enrichment ---
    "backfill-enrich-batch": {
        "task": "apps.pricing.backfill.enrichment.enrich_batch",
        "schedule": crontab(minute="*/15"),
        "kwargs": {"batch_size": 100},
        "options": {"queue": "scraping"},
    },
    "backfill-cleanup-stale": {
        "task": "apps.pricing.backfill.enrichment.cleanup_stale_enrichments",
        "schedule": crontab(minute=30, hour="*/1"),
    },
    "backfill-check-reviews": {
        "task": "apps.pricing.backfill.enrichment.check_review_completion",
        "schedule": crontab(minute="*/15"),
    },
    # --- Missing periodic tasks ---
    "expire-reward-points-monthly": {
        "task": "apps.rewards.tasks.expire_points",
        "schedule": crontab(minute=0, hour=2, day_of_month=1),  # 1st of month, 02:00 UTC
    },
    "check-return-window-alerts-daily": {
        "task": "apps.email_intel.tasks.check_return_window_alerts",
        "schedule": crontab(minute=0, hour=6),  # daily 06:00 UTC
        "options": {"queue": "alerts"},
    },
    "detect-refund-delays-daily": {
        "task": "apps.email_intel.tasks.detect_refund_delays",
        "schedule": crontab(minute=30, hour=6),  # daily 06:30 UTC
        "options": {"queue": "alerts"},
    },
    "recompute-brand-trust-weekly": {
        "task": "apps.scoring.tasks.recompute_brand_trust_scores",
        "schedule": crontab(minute=0, hour=2, day_of_week="sunday"),  # Sunday 02:00 UTC
        "options": {"queue": "scoring"},
    },
}

# ---------------------------------------------------------------------------
# Discord webhook notifications for all task events
# ---------------------------------------------------------------------------

_discord_logger = logging.getLogger("whydud.celery.discord")

# Internal Celery tasks we don't want notifications for
_IGNORED_TASKS = frozenset(
    {
        "celery.backend_cleanup",
        "celery.chord_unlock",
        "celery.accumulate",
        "celery.group",
        "celery.chain",
    }
)


def _task_queue(sender) -> str:
    """Best-effort extraction of the queue name from a task."""
    try:
        return getattr(sender, "queue", "") or getattr(sender.request, "delivery_info", {}).get("routing_key", "")
    except Exception:
        return ""


def _task_worker(sender) -> str:
    try:
        return sender.request.hostname or ""
    except Exception:
        return ""


@task_success.connect
def _on_task_success(sender=None, result=None, **kwargs):
    if sender and sender.name in _IGNORED_TASKS:
        return
    try:
        from common.discord import notify_task_success

        runtime = getattr(sender.request, "runtime", None) if sender else None
        notify_task_success(
            task_name=sender.name if sender else "unknown",
            result=result,
            runtime=runtime,
            worker=_task_worker(sender),
            queue=_task_queue(sender),
        )
    except Exception:
        _discord_logger.warning("Discord success notification failed", exc_info=True)


@task_failure.connect
def _on_task_failure(sender=None, exception=None, traceback=None, **kwargs):
    if sender and sender.name in _IGNORED_TASKS:
        return
    try:
        from common.discord import notify_task_failure

        tb_str = ""
        if traceback is not None:
            import traceback as tb_mod

            tb_str = "".join(tb_mod.format_tb(traceback)) if hasattr(traceback, "tb_frame") else str(traceback)

        notify_task_failure(
            task_name=sender.name if sender else "unknown",
            exception=str(exception) if exception else "Unknown error",
            traceback_str=tb_str,
            worker=_task_worker(sender),
            queue=_task_queue(sender),
        )
    except Exception:
        _discord_logger.warning("Discord failure notification failed", exc_info=True)


@task_retry.connect
def _on_task_retry(sender=None, reason=None, request=None, **kwargs):
    if sender and sender.name in _IGNORED_TASKS:
        return
    try:
        from common.discord import notify_task_retry

        retries = 0
        if request:
            retries = getattr(request, "retries", 0)
        elif sender:
            retries = getattr(sender.request, "retries", 0)

        notify_task_retry(
            task_name=sender.name if sender else "unknown",
            reason=str(reason) if reason else "Unknown",
            retries=retries,
            worker=_task_worker(sender),
            queue=_task_queue(sender),
        )
    except Exception:
        _discord_logger.warning("Discord retry notification failed", exc_info=True)
