"""Seed additional reserved usernames for shopping email addresses.

Adds: postmaster, webmaster, hello, test, pop, imap
"""
from django.db import migrations

ADDITIONAL_RESERVED = [
    "postmaster", "webmaster", "hello", "test", "pop", "imap",
]


def seed(apps, schema_editor):
    ReservedUsername = apps.get_model("accounts", "ReservedUsername")
    objs = [ReservedUsername(username=u) for u in ADDITIONAL_RESERVED]
    ReservedUsername.objects.bulk_create(objs, ignore_conflicts=True)


def unseed(apps, schema_editor):
    ReservedUsername = apps.get_model("accounts", "ReservedUsername")
    ReservedUsername.objects.filter(username__in=ADDITIONAL_RESERVED).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0007_alter_user_referral_code"),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
