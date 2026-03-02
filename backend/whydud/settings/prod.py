"""Production settings."""
import os
from urllib.parse import urlparse

from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get(
        "DJANGO_ALLOWED_HOSTS", "whydud.com,www.whydud.com"
    ).split(",")
    if h.strip()
] + [
    # Internal Docker hostnames — Next.js SSR calls backend via container name
    "backend",
    "localhost",
]

# Gunicorn serves behind Caddy, so trust X-Forwarded-For
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# CSRF — required behind Cloudflare proxy
CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "https://whydud.com,https://www.whydud.com",
    ).split(",")
    if o.strip()
]

# CORS — allow frontend origin
CORS_ALLOWED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "CORS_ALLOWED_ORIGINS",
        "https://whydud.com,https://www.whydud.com",
    ).split(",")
    if o.strip()
]
CORS_ALLOW_CREDENTIALS = True


# ---------------------------------------------------------------------------
# Database — parse DATABASE_URL (set by Docker Compose)
# ---------------------------------------------------------------------------

def _parse_db_url(url: str) -> dict:
    """Parse a postgres:// URL into Django DATABASES dict format."""
    parsed = urlparse(url)
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": parsed.path.lstrip("/"),
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "localhost",
        "PORT": str(parsed.port or 5432),
        "OPTIONS": {
            "options": "-c search_path=public,users,email_intel,scoring,tco,community,admin",
        },
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }


_db_url = os.environ.get("DATABASE_URL")
if _db_url:
    DATABASES["default"] = _parse_db_url(_db_url)

_write_url = os.environ.get("DATABASE_WRITE_URL")
if _write_url:
    DATABASES["write"] = _parse_db_url(_write_url)
    DATABASE_ROUTERS = ["whydud.db_router.PrimaryReplicaRouter"]


# ---------------------------------------------------------------------------
# Static files — WhiteNoise (serves Django admin CSS/JS from Gunicorn)
# ---------------------------------------------------------------------------

MIDDLEWARE.insert(
    MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
    "whitenoise.middleware.WhiteNoiseMiddleware",
)
STORAGES = {
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}
