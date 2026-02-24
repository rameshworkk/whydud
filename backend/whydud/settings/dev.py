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

# Trust X-Forwarded-Host from the Next.js proxy so AllAuth builds
# callback URLs pointing to localhost:3000 (matching Google Console)
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Show emails in console during dev
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Looser CORS in dev
CORS_ALLOW_ALL_ORIGINS = True

# Django Debug Toolbar (optional, add if installed)
# INSTALLED_APPS += ["debug_toolbar"]
# MIDDLEWARE = ["debug_toolbar.middleware.DebugToolbarMiddleware"] + MIDDLEWARE
# INTERNAL_IPS = ["127.0.0.1"]
