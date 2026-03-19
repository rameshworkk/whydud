"""Add EnrichmentPriorityRule model for admin-configurable priority rules."""
import uuid

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0011_backfillproduct_parallel_worker_statuses"),
    ]

    operations = [
        migrations.CreateModel(
            name="EnrichmentPriorityRule",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "name",
                    models.CharField(
                        help_text="Human-readable rule name (e.g. 'Apple phones > ₹50K → P1')",
                        max_length=200,
                    ),
                ),
                ("is_active", models.BooleanField(default=True)),
                (
                    "order",
                    models.IntegerField(
                        default=0,
                        help_text="Evaluation order — lower runs first. Later rules can override earlier ones.",
                    ),
                ),
                (
                    "marketplace_slug",
                    models.CharField(
                        blank=True,
                        help_text="Filter by marketplace (e.g. 'amazon-in', 'flipkart'). Blank = any.",
                        max_length=50,
                    ),
                ),
                (
                    "category_name",
                    models.CharField(
                        blank=True,
                        help_text="Exact category match (e.g. 'smartphone', 'laptop'). Blank = any.",
                        max_length=100,
                    ),
                ),
                (
                    "category_pattern",
                    models.CharField(
                        blank=True,
                        help_text="Regex pattern for category (e.g. 'smartphone|laptop'). Blank = any.",
                        max_length=200,
                    ),
                ),
                (
                    "brand_pattern",
                    models.CharField(
                        blank=True,
                        help_text="Regex pattern for title/brand (e.g. '^(apple|samsung)'). Blank = any.",
                        max_length=200,
                    ),
                ),
                (
                    "title_contains",
                    models.CharField(
                        blank=True,
                        help_text="Case-insensitive substring match on title. Blank = any.",
                        max_length=200,
                    ),
                ),
                (
                    "min_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Minimum current_price in paisa (e.g. 5000000 = ₹50K). Null = no minimum.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "max_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Maximum current_price in paisa. Null = no maximum.",
                        max_digits=12,
                        null=True,
                    ),
                ),
                (
                    "min_data_points",
                    models.IntegerField(
                        blank=True,
                        help_text="Minimum price_data_points. Null = no minimum.",
                        null=True,
                    ),
                ),
                (
                    "target_priority",
                    models.SmallIntegerField(
                        choices=[
                            (0, "P0 — On-demand"),
                            (1, "P1 — Playwright"),
                            (2, "P2 — curl_cffi"),
                            (3, "P3 — curl_cffi-low"),
                        ],
                        help_text="Priority to assign to matching products.",
                    ),
                ),
                (
                    "also_mark_reviews",
                    models.BooleanField(
                        default=False,
                        help_text="Also set review_status='pending' for matched products.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "enrichment_priority_rules",
                "ordering": ["order", "created_at"],
            },
        ),
    ]
