"""Celery application configuration for Whydud."""
import os

from celery import Celery
from celery.schedules import crontab

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.dev")

app = Celery("whydud")

# Load config from Django settings, using CELERY_ namespace.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Autodiscover tasks in all installed apps.
app.autodiscover_tasks()

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
    "detect-deals-2h": {
        "task": "apps.deals.tasks.detect_blockbuster_deals",
        "schedule": crontab(minute=0, hour="*/2"),  # every 2 hours at :00
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
}
