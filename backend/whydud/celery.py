"""Celery application configuration for Whydud."""
import os

from celery import Celery

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
    # TODO Sprint 2: "scrape-daily": { ... }
    # TODO Sprint 3: "price-alerts-4h": { ... }
    # TODO Sprint 4: "deal-detection-30m": { ... }
}
