"""Seed initial marketplace data.

Populates Amazon.in and Flipkart — the two primary scraped marketplaces
at Sprint 1. Additional marketplaces (Croma, Myntra, etc.) added in Sprint 2.
"""
from django.db import migrations

MARKETPLACES = [
    {
        "slug": "amazon_in",
        "name": "Amazon.in",
        "base_url": "https://www.amazon.in",
        "affiliate_tag": "",          # set via env/admin after launch
        "affiliate_param": "tag",
        "scraper_status": "active",
    },
    {
        "slug": "flipkart",
        "name": "Flipkart",
        "base_url": "https://www.flipkart.com",
        "affiliate_tag": "",
        "affiliate_param": "affid",
        "scraper_status": "active",
    },
    {
        "slug": "croma",
        "name": "Croma",
        "base_url": "https://www.croma.com",
        "affiliate_tag": "",
        "affiliate_param": "utm_source",
        "scraper_status": "pending",
    },
    {
        "slug": "reliance_digital",
        "name": "Reliance Digital",
        "base_url": "https://www.reliancedigital.in",
        "affiliate_tag": "",
        "affiliate_param": "utm_source",
        "scraper_status": "pending",
    },
    {
        "slug": "meesho",
        "name": "Meesho",
        "base_url": "https://www.meesho.com",
        "affiliate_tag": "",
        "affiliate_param": "utm_source",
        "scraper_status": "pending",
    },
]


def seed_marketplaces(apps, schema_editor):
    Marketplace = apps.get_model("products", "Marketplace")
    for data in MARKETPLACES:
        Marketplace.objects.update_or_create(
            slug=data["slug"],
            defaults=data,
        )


def remove_seeded_marketplaces(apps, schema_editor):
    Marketplace = apps.get_model("products", "Marketplace")
    Marketplace.objects.filter(slug__in=[m["slug"] for m in MARKETPLACES]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_marketplaces, remove_seeded_marketplaces),
    ]
