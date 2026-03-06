"""Flower configuration for Celery monitoring.

Flower reads this file automatically when started with:
    celery -A whydud flower --conf=whydud/flowerconfig.py

Or via environment variable:
    FLOWER_CONF=whydud/flowerconfig.py celery -A whydud flower
"""
import os

# ---------------------------------------------------------------------------
# Authentication — basic auth for admin access
# ---------------------------------------------------------------------------
# Set via env vars in production. Dev defaults to admin/admin.
basic_auth = [
    os.environ.get("FLOWER_BASIC_AUTH", "admin:admin"),
]

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
port = int(os.environ.get("FLOWER_PORT", "5555"))
address = "0.0.0.0"

# ---------------------------------------------------------------------------
# Broker (Redis)
# ---------------------------------------------------------------------------
broker_api = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Persistent task storage
# ---------------------------------------------------------------------------
# Keep task history in a local SQLite DB so it survives Flower restarts.
persistent = True
db = os.environ.get("FLOWER_DB", "flower.db")
state_save_interval = 10000.0  # save state every 10 seconds (ms)

# ---------------------------------------------------------------------------
# Task defaults
# ---------------------------------------------------------------------------
# Max number of tasks to keep in memory (prevents OOM on high-volume queues).
max_tasks = 50000

# How far back to look when Flower connects to the broker (seconds).
# 3 days = good balance between history and memory.
inspect_timeout = 10000.0  # 10s timeout for worker inspection (ms)

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
auto_refresh = True

# ---------------------------------------------------------------------------
# Task columns — show the most useful info by default
# ---------------------------------------------------------------------------
natural_time = True

# ---------------------------------------------------------------------------
# URL prefix — useful when behind a reverse proxy
# ---------------------------------------------------------------------------
url_prefix = os.environ.get("FLOWER_URL_PREFIX", "")

# ---------------------------------------------------------------------------
# Purge offline workers after this many hours (keeps UI clean)
# ---------------------------------------------------------------------------
purge_offline_workers = int(os.environ.get("FLOWER_PURGE_OFFLINE_WORKERS", "24"))
