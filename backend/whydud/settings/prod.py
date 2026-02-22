"""Production settings."""
from .base import *  # noqa: F401, F403

DEBUG = False

ALLOWED_HOSTS = [
    "whydud.com",
    "www.whydud.com",
    "api.whydud.com",
]

# Gunicorn serves behind Caddy, so trust X-Forwarded-For
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
