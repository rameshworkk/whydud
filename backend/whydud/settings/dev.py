"""Development settings."""
from .base import *  # noqa: F401, F403

DEBUG = True
ALLOWED_HOSTS = ["*"]

# Disable HTTPS requirements in dev
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
SECURE_HSTS_SECONDS = 0

# CSRF: trust the Next.js dev server origin
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

# OAuth requires Lax (not Strict) so session cookie survives the Google redirect
SESSION_COOKIE_SAMESITE = "Lax"

# Show emails in console during dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Looser CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optional, add if installed)
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
# INTERNAL_IPS = ["127.0.0.1"]
