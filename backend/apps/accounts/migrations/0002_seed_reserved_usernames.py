"""Seed the users.reserved_usernames table with blocked shopping email usernames.

These usernames cannot be registered by end users.
"""
from django.db import migrations

# Usernames permanently reserved — system, brand, abuse-prevention terms
RESERVED_USERNAMES = [
    # System / infrastructure
    "admin", "administrator", "superuser", "staff", "root", "system",
    "bot", "daemon", "service", "api", "webhook", "callback",
    # Platform brand
    "whydud", "whyd", "whydudcom", "whydud_team",
    # Communication channels
    "support", "help", "contact", "feedback", "complaints",
    "info", "information", "news", "updates", "status",
    "noreply", "no-reply", "donotreply", "do-not-reply",
    # Business / legal
    "billing", "sales", "marketing", "legal", "privacy",
    "security", "abuse", "spam", "dmca", "copyright",
    "press", "media", "pr", "investors",
    # Product features (avoid impersonation)
    "inbox", "deals", "rewards", "alerts", "notifications",
    "search", "dashboard", "profile", "settings", "account",
    "moderator", "mod", "team", "official",
    # Reserved for future internal use
    "www", "mail", "email", "smtp", "ftp", "cdn",
    "static", "assets", "images", "files",
    # Short / ambiguous
    "me", "you", "us", "we",
]


def seed_reserved_usernames(apps, schema_editor):
    ReservedUsername = apps.get_model("accounts", "ReservedUsername")
    objs = [ReservedUsername(username=u) for u in RESERVED_USERNAMES]
    ReservedUsername.objects.bulk_create(objs, ignore_conflicts=True)


def remove_seeded_usernames(apps, schema_editor):
    ReservedUsername = apps.get_model("accounts", "ReservedUsername")
    ReservedUsername.objects.filter(username__in=RESERVED_USERNAMES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_reserved_usernames, remove_seeded_usernames),
    ]
