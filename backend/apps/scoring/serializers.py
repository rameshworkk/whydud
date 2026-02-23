"""Serializers for the scoring app."""
from rest_framework import serializers

from .models import DudScoreConfig


class DudScoreConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = DudScoreConfig
        fields = [
            "id", "version",
            "w_sentiment", "w_rating_quality", "w_price_value",
            "w_review_credibility", "w_price_stability", "w_return_signal",
            "fraud_penalty_threshold", "min_review_threshold",
            "cold_start_penalty", "anomaly_spike_threshold",
            "is_active", "activated_at", "change_reason", "created_at",
        ]
        read_only_fields = ["id", "version", "is_active", "activated_at", "created_at"]
