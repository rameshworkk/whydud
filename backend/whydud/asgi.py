"""ASGI config for whydud project."""
import os

from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "whydud.settings.prod")

application = get_asgi_application()
