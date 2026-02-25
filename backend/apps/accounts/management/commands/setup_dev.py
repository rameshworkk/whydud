"""One-command dev environment setup.

Run after fresh migrations to restore all manual configuration:
    python manage.py setup_dev

Idempotent — safe to run multiple times.
"""

import os

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Configure Site, OAuth, superuser, and seed data for local dev."

    def handle(self, *args, **options):
        self._setup_site()
        self._setup_google_oauth()
        self._setup_superuser()
        self._run_seed_data()
        self.stdout.write(self.style.SUCCESS("\nDev setup complete."))

    def _setup_site(self):
        from django.contrib.sites.models import Site

        site = Site.objects.get(id=1)
        site.domain = "localhost:8000"
        site.name = "Whydud Dev"
        site.save()
        self.stdout.write(f"  Site: {site.domain}")

    def _setup_google_oauth(self):
        from allauth.socialaccount.models import SocialApp

        # allauth 65+ reads Google credentials from SOCIALACCOUNT_PROVIDERS
        # in settings.py. A DB SocialApp would cause MultipleObjectsReturned.
        # Clean up any stale DB entries.
        deleted, _ = SocialApp.objects.filter(provider="google").delete()
        if deleted:
            self.stdout.write(f"  Google OAuth: removed {deleted} stale DB entry(s)")
        self.stdout.write("  Google OAuth: configured via settings.py (SOCIALACCOUNT_PROVIDERS)")

    def _setup_superuser(self):
        from apps.accounts.models import User

        email = "admin@whydud.com"
        if User.objects.filter(email=email).exists():
            self.stdout.write(f"  Superuser: {email} (already exists)")
            return

        User.objects.create_superuser(email=email, password="admin123")
        self.stdout.write(f"  Superuser: {email} / admin123")

    def _run_seed_data(self):
        from django.core.management import call_command

        call_command("seed_data")
        self.stdout.write("  Seed data: loaded")
