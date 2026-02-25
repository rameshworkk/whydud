"""Base Django settings shared across all environments."""
import os
from pathlib import Path

import structlog

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "INSECURE-change-in-production")

DEBUG = False

ALLOWED_HOSTS: list[str] = []

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------

DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",
    "django.contrib.postgres",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework.authtoken",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.products",
    "apps.pricing",
    "apps.reviews",
    "apps.scoring",
    "apps.email_intel",
    "apps.wishlists",
    "apps.deals",
    "apps.rewards",
    "apps.discussions",
    "apps.tco",
    "apps.search",
    "apps.scraping",
    "apps.admin_tools",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "whydud.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "whydud.wsgi.application"
ASGI_APPLICATION = "whydud.asgi.application"

# ---------------------------------------------------------------------------
# Database — PostgreSQL 16 + TimescaleDB
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.environ.get("POSTGRES_DB", "whydud"),
        "USER": os.environ.get("POSTGRES_USER", "whydud"),
        "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "whydud"),
        "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
        "PORT": os.environ.get("POSTGRES_PORT", "5432"),
        "OPTIONS": {
            "options": "-c search_path=public,users,email_intel,scoring,tco,community,admin",
        },
        "CONN_MAX_AGE": 60,
        "CONN_HEALTH_CHECKS": True,
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cache + Session — Redis
# ---------------------------------------------------------------------------

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "db": "1",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Strict"

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------

CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = "django-db"
CELERY_CACHE_BACKEND = "default"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 minutes soft limit

# ---------------------------------------------------------------------------
# Frontend URL (for email links: verification, password reset, etc.)
# ---------------------------------------------------------------------------

FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:3000")

# AllAuth OAuth redirects here after Google login.
# This is a Django view that creates a one-time code and redirects to the frontend.
LOGIN_REDIRECT_URL = "/oauth/complete/"

# Password reset token validity (seconds) — 24 hours
PASSWORD_RESET_TIMEOUT = 86400

# ---------------------------------------------------------------------------
# Auth — Django AllAuth
# ---------------------------------------------------------------------------

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

SITE_ID = 1

ACCOUNT_USER_MODEL_USERNAME_FIELD = None
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = "mandatory"

# Social accounts (Google) skip email verification — provider already verified it
SOCIALACCOUNT_EMAIL_VERIFICATION = "none"
SOCIALACCOUNT_AUTO_SIGNUP = True
SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "SCOPE": ["profile", "email"],
        "AUTH_PARAMS": {"access_type": "online"},
        "APP": {
            "client_id": os.environ.get("GOOGLE_CLIENT_ID", ""),
            "secret": os.environ.get("GOOGLE_CLIENT_SECRET", ""),
        },
    }
}

# Allow OAuth login via GET (no intermediate confirmation page)
SOCIALACCOUNT_LOGIN_ON_GET = True

# Auto-connect social account if email matches existing user
SOCIALACCOUNT_EMAIL_AUTHENTICATION_AUTO_CONNECT = True

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_PAGINATION_CLASS": "common.pagination.CursorPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "10/min",
        "user": "30/min",
    },
    "EXCEPTION_HANDLER": "common.utils.custom_exception_handler",
}

# ---------------------------------------------------------------------------
# Meilisearch
# ---------------------------------------------------------------------------

MEILISEARCH_URL = os.environ.get("MEILISEARCH_URL", "http://localhost:7700")
MEILISEARCH_MASTER_KEY = os.environ.get("MEILISEARCH_MASTER_KEY", "")

# ---------------------------------------------------------------------------
# Email — Resend
# ---------------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = "smtp.resend.com"
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = "resend"
EMAIL_HOST_PASSWORD = os.environ.get("RESEND_API_KEY", "")
DEFAULT_FROM_EMAIL = "noreply@whydud.com"

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Strict"

SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Encryption keys (AES-256-GCM for email bodies + OAuth tokens)
# ---------------------------------------------------------------------------

EMAIL_ENCRYPTION_KEY = os.environ.get("EMAIL_ENCRYPTION_KEY", "")
OAUTH_ENCRYPTION_KEY = os.environ.get("OAUTH_ENCRYPTION_KEY", "")

# ---------------------------------------------------------------------------
# Cloudflare Email Worker webhook secret
# ---------------------------------------------------------------------------

CLOUDFLARE_EMAIL_WEBHOOK_SECRET = os.environ.get("CLOUDFLARE_EMAIL_WEBHOOK_SECRET", "")

# ---------------------------------------------------------------------------
# Resend (transactional email sending from @whyd.* addresses)
# ---------------------------------------------------------------------------

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")

# ---------------------------------------------------------------------------
# Razorpay
# ---------------------------------------------------------------------------

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "")

# ---------------------------------------------------------------------------
# Structlog
# ---------------------------------------------------------------------------

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------

CORS_ALLOWED_ORIGINS = [
    os.environ.get("FRONTEND_URL", "http://localhost:3000"),
]
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Pagination
# All page-size limits are driven by these settings and overridable via env
# vars.  Sprint 4 admin panel will surface these as editable SiteConfig rows.
# ---------------------------------------------------------------------------

PAGINATION_PAGE_SIZE = int(os.environ.get("PAGINATION_PAGE_SIZE", "20"))
PAGINATION_MAX_PAGE_SIZE = int(os.environ.get("PAGINATION_MAX_PAGE_SIZE", "100"))

# ---------------------------------------------------------------------------
# Product list
# ---------------------------------------------------------------------------

PRODUCT_LIST_PAGE_SIZE = int(os.environ.get("PRODUCT_LIST_PAGE_SIZE", "24"))
PRODUCT_LIST_PAGE_SIZE_MAX = int(os.environ.get("PRODUCT_LIST_PAGE_SIZE_MAX", "100"))

# Default ordering when no sort_by param is supplied.
PRODUCT_LIST_DEFAULT_ORDERING: str = os.environ.get(
    "PRODUCT_LIST_DEFAULT_ORDERING", "-dud_score"
)

# Allowed sort_by values → ORM ordering expressions.
# Keys become the public API enum; values are passed to queryset.order_by().
PRODUCT_SORT_OPTIONS: dict[str, list[str]] = {
    "dud_score": ["-dud_score"],
    "price_asc": ["current_best_price"],
    "price_desc": ["-current_best_price"],
    "newest": ["-created_at"],
    "top_rated": ["-avg_rating"],
}

# ---------------------------------------------------------------------------
# Search & Autocomplete
# ---------------------------------------------------------------------------

SEARCH_PAGE_SIZE_DEFAULT = int(os.environ.get("SEARCH_PAGE_SIZE_DEFAULT", "20"))
SEARCH_PAGE_SIZE_MAX = int(os.environ.get("SEARCH_PAGE_SIZE_MAX", "100"))
SEARCH_AUTOCOMPLETE_LIMIT = int(os.environ.get("SEARCH_AUTOCOMPLETE_LIMIT", "8"))
SEARCH_MIN_QUERY_LENGTH = int(os.environ.get("SEARCH_MIN_QUERY_LENGTH", "2"))

# Meilisearch sort param strings for each public sort_by value.
SEARCH_SORT_MAP_MEILI: dict[str, list[str]] = {
    "relevance": [],
    "price_asc": ["current_best_price:asc"],
    "price_desc": ["current_best_price:desc"],
    "dud_score": ["dud_score:desc"],
    "top_rated": ["avg_rating:desc"],
}
