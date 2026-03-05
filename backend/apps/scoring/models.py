"""DudScore configuration, history, and Brand Trust Score models.

PostgreSQL schema: scoring
"""
import uuid
from django.db import models

class DudScoreConfig(models.Model):
    """Versioned DudScore weight configuration."""
    version = models.IntegerField()
    w_sentiment = models.DecimalField(max_digits=4, decimal_places=3)
    w_rating_quality = models.DecimalField(max_digits=4, decimal_places=3)
    w_price_value = models.DecimalField(max_digits=4, decimal_places=3)
    w_review_credibility = models.DecimalField(max_digits=4, decimal_places=3)
    w_price_stability = models.DecimalField(max_digits=4, decimal_places=3)
    w_return_signal = models.DecimalField(max_digits=4, decimal_places=3)
    fraud_penalty_threshold = models.DecimalField(max_digits=3, decimal_places=2)
    min_review_threshold = models.IntegerField()
    cold_start_penalty = models.DecimalField(max_digits=3, decimal_places=2)
    anomaly_spike_threshold = models.DecimalField(max_digits=5, decimal_places=2)
    is_active = models.BooleanField(default=False)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_by = models.UUIDField(null=True, blank=True)
    change_reason = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'scoring"."dudscore_config'

    def __str__(self) -> str:
        return f"DudScore Config v{self.version} (active={self.is_active})"


class DudScoreHistory(models.Model):
    """TimescaleDB hypertable for tracking score changes over time."""
    time = models.DateTimeField()
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    score = models.DecimalField(max_digits=5, decimal_places=2)
    config_version = models.IntegerField()
    component_scores = models.JSONField()

    class Meta:
        db_table = 'scoring"."dudscore_history'
        managed = False  # TimescaleDB hypertable


class BrandTrustScore(models.Model):
    """Aggregated trust score for a brand, computed weekly from product DudScores.

    Only brands with >= 5 DudScore-rated products are scored.
    """

    class TrustTier(models.TextChoices):
        EXCELLENT = "excellent", "Excellent"
        GOOD = "good", "Good"
        AVERAGE = "average", "Average"
        POOR = "poor", "Poor"
        AVOID = "avoid", "Avoid"

    brand = models.OneToOneField(
        "products.Brand",
        on_delete=models.CASCADE,
        related_name="trust_score",
    )
    avg_dud_score = models.DecimalField(
        max_digits=5, decimal_places=2,
        help_text="Average DudScore across all scored products.",
    )
    product_count = models.IntegerField(
        help_text="Number of products with a DudScore for this brand.",
    )
    avg_fake_review_pct = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Average percentage of flagged reviews across products.",
    )
    avg_price_stability = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="Average price stability component (0-100) from DudScores.",
    )
    quality_consistency = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True,
        help_text="STDDEV of DudScores — lower = more consistent.",
    )
    trust_tier = models.CharField(
        max_length=20,
        choices=TrustTier.choices,
        help_text="Derived tier: excellent (>=80), good (>=65), average (>=50), poor (>=35), avoid (<35).",
    )
    computed_at = models.DateTimeField(
        help_text="When this score was last computed.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scoring"."brand_trust_scores'
        indexes = [
            models.Index(fields=["-avg_dud_score"]),
            models.Index(fields=["trust_tier"]),
        ]

    def __str__(self) -> str:
        return f"{self.brand.name}: {self.avg_dud_score} ({self.trust_tier})"
