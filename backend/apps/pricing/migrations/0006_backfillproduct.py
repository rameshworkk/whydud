# Generated manually for backfill pipeline

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0005_add_source_to_price_snapshots"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BackfillProduct",
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
                ("ph_code", models.CharField(db_index=True, max_length=20, unique=True)),
                ("ph_url", models.URLField(blank=True, max_length=500)),
                ("marketplace_slug", models.CharField(db_index=True, max_length=50)),
                ("external_id", models.CharField(db_index=True, max_length=200)),
                ("marketplace_url", models.URLField(blank=True, max_length=2000)),
                ("title", models.CharField(blank=True, max_length=1000)),
                ("brand_name", models.CharField(blank=True, max_length=200)),
                ("image_url", models.URLField(blank=True, max_length=500)),
                (
                    "product_listing",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="backfill_records",
                        to="products.productlisting",
                    ),
                ),
                ("price_data_points", models.IntegerField(default=0)),
                ("history_from", models.DateTimeField(blank=True, null=True)),
                ("history_to", models.DateTimeField(blank=True, null=True)),
                ("bh_prediction_days", models.IntegerField(blank=True, null=True)),
                ("bh_prediction_weeks", models.IntegerField(blank=True, null=True)),
                ("bh_prediction_months", models.IntegerField(blank=True, null=True)),
                ("bh_popularity", models.IntegerField(blank=True, null=True)),
                (
                    "min_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                (
                    "max_price",
                    models.DecimalField(
                        blank=True, decimal_places=2, max_digits=12, null=True
                    ),
                ),
                ("min_price_date", models.DateTimeField(blank=True, null=True)),
                ("max_price_date", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("discovered", "Discovered"),
                            ("bh_filled", "BuyHatke Filled"),
                            ("ph_extended", "PH Extended"),
                            ("done", "Done"),
                            ("failed", "Failed"),
                            ("skipped", "Skipped"),
                        ],
                        default="discovered",
                        max_length=20,
                    ),
                ),
                ("error_message", models.TextField(blank=True)),
                ("retry_count", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "backfill_products",
                "indexes": [
                    models.Index(
                        fields=["status", "marketplace_slug"],
                        name="pricing_back_status_3c9a7e_idx",
                    ),
                    models.Index(
                        fields=["external_id", "marketplace_slug"],
                        name="pricing_back_externa_f5c1d8_idx",
                    ),
                ],
            },
        ),
    ]
