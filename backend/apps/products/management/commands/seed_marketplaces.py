"""Seed all 12 Indian marketplaces.

Usage:
    python manage.py seed_marketplaces
"""

from django.core.management.base import BaseCommand

from apps.products.models import Marketplace

MARKETPLACES = [
    {
        "slug": "amazon_in",
        "name": "Amazon.in",
        "base_url": "https://www.amazon.in",
        "affiliate_param": "tag",
        "affiliate_tag": "whydud-21",
        "scraper_status": "active",
    },
    {
        "slug": "flipkart",
        "name": "Flipkart",
        "base_url": "https://www.flipkart.com",
        "affiliate_param": "affid",
        "affiliate_tag": "whydud",
        "scraper_status": "active",
    },
    {
        "slug": "croma",
        "name": "Croma",
        "base_url": "https://www.croma.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "reliance_digital",
        "name": "Reliance Digital",
        "base_url": "https://www.reliancedigital.in",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "vijay_sales",
        "name": "Vijay Sales",
        "base_url": "https://www.vijaysales.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "tata_cliq",
        "name": "Tata CLiQ",
        "base_url": "https://www.tatacliq.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "jiomart",
        "name": "JioMart",
        "base_url": "https://www.jiomart.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "myntra",
        "name": "Myntra",
        "base_url": "https://www.myntra.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "nykaa",
        "name": "Nykaa",
        "base_url": "https://www.nykaa.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "ajio",
        "name": "AJIO",
        "base_url": "https://www.ajio.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "meesho",
        "name": "Meesho",
        "base_url": "https://www.meesho.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "snapdeal",
        "name": "Snapdeal",
        "base_url": "https://www.snapdeal.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
]


class Command(BaseCommand):
    help = "Seed all 12 Indian marketplaces (update_or_create by slug)"

    def handle(self, *args, **options):
        created = 0
        updated = 0
        for data in MARKETPLACES:
            slug = data.pop("slug")
            _, was_created = Marketplace.objects.update_or_create(
                slug=slug, defaults=data
            )
            data["slug"] = slug  # restore for idempotency
            if was_created:
                created += 1
            else:
                updated += 1

        total = Marketplace.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"Marketplaces: {total} total ({created} created, {updated} updated)"
            )
        )
