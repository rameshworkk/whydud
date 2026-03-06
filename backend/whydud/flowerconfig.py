"""Flower configuration for Celery monitoring.

NOTE: Only put settings here that Tornado's config parser won't reject.
Numeric options with strict type requirements are passed as CLI args
in docker-compose instead (see flower service command).

Flower reads this file automatically when started with:
    celery -A whydud flower --conf=whydud/flowerconfig.py
"""
import os

# ---------------------------------------------------------------------------
# Authentication — basic auth for admin access
# ---------------------------------------------------------------------------
basic_auth = [
    os.environ.get("FLOWER_BASIC_AUTH", "admin:admin"),
]

# ---------------------------------------------------------------------------
# Server
# ---------------------------------------------------------------------------
address = "0.0.0.0"

# ---------------------------------------------------------------------------
# Broker (Redis)
# ---------------------------------------------------------------------------
broker_api = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

# ---------------------------------------------------------------------------
# Persistent task storage
# ---------------------------------------------------------------------------
persistent = True
db = os.environ.get("FLOWER_DB", "flower.db")

# ---------------------------------------------------------------------------
# Auto-refresh
# ---------------------------------------------------------------------------
auto_refresh = True

# ---------------------------------------------------------------------------
# Task columns
# ---------------------------------------------------------------------------
natural_time = True

# ---------------------------------------------------------------------------
# URL prefix — useful when behind a reverse proxy
# ---------------------------------------------------------------------------
url_prefix = os.environ.get("FLOWER_URL_PREFIX", "")
