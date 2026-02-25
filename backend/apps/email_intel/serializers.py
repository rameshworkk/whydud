"""Serializers for the email_intel app."""
from rest_framework import serializers

from .models import DetectedSubscription, InboxEmail, ParsedOrder, RefundTracking, ReturnWindow


class InboxEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxEmail
        fields = [
            "id", "sender_address", "sender_name", "subject",
            "received_at", "category", "marketplace", "confidence",
            "parse_status", "parsed_entity_type", "parsed_entity_id",
            "is_read", "is_starred", "has_attachments", "raw_size_bytes",
            "created_at",
        ]
        read_only_fields = [
            "id", "sender_address", "sender_name", "subject", "received_at",
            "category", "marketplace", "parse_status", "parsed_entity_type",
            "parsed_entity_id", "has_attachments", "raw_size_bytes", "created_at",
        ]


class ParsedOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParsedOrder
        fields = [
            "id", "source", "order_id", "marketplace", "product_name",
            "quantity", "price_paid", "tax", "shipping_cost", "total_amount",
            "currency", "order_date", "delivery_date", "seller_name",
            "payment_method", "matched_product", "match_confidence",
            "match_status", "created_at",
        ]


class RefundTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundTracking
        fields = [
            "id", "status", "refund_amount",
            "initiated_at", "expected_by", "completed_at",
            "marketplace", "delay_days", "created_at",
        ]


class ReturnWindowSerializer(serializers.ModelSerializer):
    days_remaining = serializers.SerializerMethodField()

    class Meta:
        model = ReturnWindow
        fields = [
            "id", "window_end_date", "is_extended",
            "days_remaining", "created_at",
        ]

    def get_days_remaining(self, obj: ReturnWindow) -> int:
        from django.utils import timezone
        today = timezone.now().date()
        delta = (obj.window_end_date - today).days
        return max(0, delta)


class DetectedSubscriptionSerializer(serializers.ModelSerializer):
    annual_cost = serializers.SerializerMethodField()

    class Meta:
        model = DetectedSubscription
        fields = [
            "id", "service_name", "amount", "currency",
            "billing_cycle", "next_renewal", "is_active",
            "annual_cost", "created_at",
        ]

    def get_annual_cost(self, obj: DetectedSubscription) -> float | None:
        if not obj.amount:
            return None
        cycle_map = {"monthly": 12, "quarterly": 4, "half_yearly": 2, "yearly": 1}
        multiplier = cycle_map.get(obj.billing_cycle, 1)
        return float(obj.amount) * multiplier


class SendEmailSerializer(serializers.Serializer):
    """Validates POST /api/v1/inbox/send (compose new email)."""
    to = serializers.EmailField()
    subject = serializers.CharField(max_length=1000)
    body_html = serializers.CharField()
    body_text = serializers.CharField(required=False, allow_blank=True, default="")


class ReplyEmailSerializer(serializers.Serializer):
    """Validates POST /api/v1/inbox/:id/reply."""
    body_html = serializers.CharField()
    body_text = serializers.CharField(required=False, allow_blank=True, default="")
