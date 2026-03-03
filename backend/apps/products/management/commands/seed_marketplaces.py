"""Seed all 12 Indian marketplaces.

Usage:
    python manage.py seed_marketplaces
"""

from django.core.management.base import BaseCommand

from apps.products.models import Marketplace

MARKETPLACES = [
    {
        "slug": "amazon-in",
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
        "slug": "reliance-digital",
        "name": "Reliance Digital",
        "base_url": "https://www.reliancedigital.in",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "vijay-sales",
        "name": "Vijay Sales",
        "base_url": "https://www.vijaysales.com",
        "affiliate_param": "utm_source",
        "scraper_status": "active",
    },
    {
        "slug": "tata-cliq",
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


_SLUG_MIGRATIONS = {
    "amazon_in": "amazon-in",
    "reliance_digital": "reliance-digital",
    "vijay_sales": "vijay-sales",
    "tata_cliq": "tata-cliq",
}


class Command(BaseCommand):
    help = "Seed all 12 Indian marketplaces (update_or_create by slug)"

    def handle(self, *args, **options):
        # Fix old underscore slugs → hyphens
        migrated = 0
        for old_slug, new_slug in _SLUG_MIGRATIONS.items():
            rows = Marketplace.objects.filter(slug=old_slug).update(slug=new_slug)
            if rows:
                migrated += rows
                self.stdout.write(f"  Migrated slug: {old_slug} → {new_slug}")

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
                f"Marketplaces: {total} total ({created} created, {updated} updated, {migrated} slug-migrated)"
            )
        )
