"""Sync all active products to the Meilisearch products index.

Usage:
    python manage.py sync_meilisearch
    python manage.py sync_meilisearch --clear   # clear index first
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.products.models import Product
from apps.products.serializers import ProductListSerializer


class Command(BaseCommand):
    help = "Sync all active products to Meilisearch index"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Delete all documents before syncing",
        )

    def handle(self, *args, **options):
        try:
            import meilisearch
        except ImportError:
            self.stderr.write(self.style.ERROR(
                "meilisearch package not installed. Run: pip install meilisearch"
            ))
            return

        url = getattr(settings, "MEILISEARCH_URL", None)
        key = getattr(settings, "MEILISEARCH_MASTER_KEY", "")
        if not url:
            self.stderr.write(self.style.ERROR(
                "MEILISEARCH_URL not set in Django settings."
            ))
            return

        client = meilisearch.Client(url, key)
        index = client.index("products")

        # Configure index settings
        self.stdout.write("Configuring index settings...")
        index.update_settings({
            "searchableAttributes": [
                "title",
                "brand_name",
                "category_name",
                "category_breadcrumb",
                "description",
            ],
            "filterableAttributes": [
                "category_slug",
                "category_parent_slug",
                "category_department_slug",
                "brand_slug",
                "current_best_price",
                "dud_score",
                "status",
                "in_stock",
                "is_lightweight",
            ],
            "sortableAttributes": [
                "current_best_price",
                "dud_score",
                "avg_rating",
                "total_reviews",
                "created_at",
            ],
            "rankingRules": [
                "words",
                "typo",
                "proximity",
                "attribute",
                "sort",
                "exactness",
                "is_lightweight:asc",
            ],
            "displayedAttributes": ["*"],
        })

        if options["clear"]:
            self.stdout.write("Clearing existing documents...")
            task = index.delete_all_documents()
            client.wait_for_task(task.task_uid, timeout_in_ms=30000)
            self.stdout.write(self.style.SUCCESS("Index cleared."))

        # Fetch all active products
        products = (
            Product.objects
            .select_related("brand", "category__parent__parent")
            .filter(status=Product.Status.ACTIVE)
        )
        total = products.count()
        self.stdout.write(f"Syncing {total} products...")

        # Serialize and send in batches
        batch_size = 500
        synced = 0
        for i in range(0, total, batch_size):
            batch = products[i:i + batch_size]
            serialized = ProductListSerializer(batch, many=True).data

            # Convert to Meilisearch document format
            documents = []
            for item in serialized:
                doc = dict(item)
                # Meilisearch needs string id
                doc["id"] = str(doc["id"])
                # Convert Decimal fields to float for JSON
                for field in ("current_best_price", "lowest_price_ever", "avg_rating", "dud_score"):
                    if doc.get(field) is not None:
                        doc[field] = float(doc[field])
                documents.append(doc)

            task = index.add_documents(documents, primary_key="id")
            client.wait_for_task(task.task_uid, timeout_in_ms=60000)

            synced += len(documents)
            self.stdout.write(f"  {synced}/{total} synced")

        self.stdout.write(self.style.SUCCESS(
            f"Done! {synced} products synced to Meilisearch."
        ))
