"""DudScore configuration and history models.

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
