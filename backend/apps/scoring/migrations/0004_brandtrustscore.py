"""Create brand_trust_scores table in scoring schema.

Stores aggregated trust scores per brand, computed weekly from product DudScores.
"""
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0003_weights_sum_constraint"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BrandTrustScore",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "avg_dud_score",
                    models.DecimalField(
                        decimal_places=2,
                        help_text="Average DudScore across all scored products.",
                        max_digits=5,
                    ),
                ),
                (
                    "product_count",
                    models.IntegerField(
                        help_text="Number of products with a DudScore for this brand.",
                    ),
                ),
                (
                    "avg_fake_review_pct",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Average percentage of flagged reviews across products.",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "avg_price_stability",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Average price stability component (0-100) from DudScores.",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "quality_consistency",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="STDDEV of DudScores — lower = more consistent.",
                        max_digits=5,
                        null=True,
                    ),
                ),
                (
                    "trust_tier",
                    models.CharField(
                        choices=[
                            ("excellent", "Excellent"),
                            ("good", "Good"),
                            ("average", "Average"),
                            ("poor", "Poor"),
                            ("avoid", "Avoid"),
                        ],
                        help_text="Derived tier: excellent (>=80), good (>=65), average (>=50), poor (>=35), avoid (<35).",
                        max_length=20,
                    ),
                ),
                (
                    "computed_at",
                    models.DateTimeField(
                        help_text="When this score was last computed.",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "brand",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="trust_score",
                        to="products.brand",
                    ),
                ),
            ],
            options={
                "db_table": 'scoring"."brand_trust_scores',
                "indexes": [
                    models.Index(
                        fields=["-avg_dud_score"],
                        name="scoring_bran_avg_dud_idx",
                    ),
                    models.Index(
                        fields=["trust_tier"],
                        name="scoring_bran_trust_t_idx",
                    ),
                ],
            },
        ),
    ]
