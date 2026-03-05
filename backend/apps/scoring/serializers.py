"""Serializers for the scoring app."""
from rest_framework import serializers

from .models import BrandTrustScore, DudScoreConfig


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


class BrandTrustScoreSerializer(serializers.ModelSerializer):
    """Serializer for brand trust score — includes nested brand fields."""

    brand_name = serializers.CharField(source="brand.name", read_only=True)
    brand_slug = serializers.CharField(source="brand.slug", read_only=True)
    brand_logo_url = serializers.URLField(source="brand.logo_url", read_only=True, allow_blank=True)
    brand_verified = serializers.BooleanField(source="brand.verified", read_only=True)

    class Meta:
        model = BrandTrustScore
        fields = [
            "id",
            "brand_name",
            "brand_slug",
            "brand_logo_url",
            "brand_verified",
            "avg_dud_score",
            "product_count",
            "avg_fake_review_pct",
            "avg_price_stability",
            "quality_consistency",
            "trust_tier",
            "computed_at",
        ]
        read_only_fields = fields
