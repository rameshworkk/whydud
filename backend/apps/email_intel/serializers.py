from rest_framework import serializers
from .models import DetectedSubscription, InboxEmail, ParsedOrder, RefundTracking, ReturnWindow

class InboxEmailSerializer(serializers.ModelSerializer):
    class Meta:
        model = InboxEmail
        fields = [
            "id", "sender_address", "sender_name", "subject",
            "received_at", "category", "marketplace",
            "parse_status", "is_read", "is_starred", "created_at",
        ]
        read_only_fields = ["id", "received_at", "created_at"]

class ParsedOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParsedOrder
        fields = [
            "id", "source", "order_id", "marketplace", "product_name",
            "quantity", "price_paid", "total_amount", "currency",
            "order_date", "delivery_date", "seller_name", "payment_method",
            "match_status", "created_at",
        ]
        read_only_fields = ["id", "source", "created_at"]

class RefundTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = RefundTracking
        fields = ["id", "status", "refund_amount", "initiated_at", "expected_by", "completed_at", "delay_days"]

class ReturnWindowSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReturnWindow
        fields = ["id", "order", "window_end_date", "is_extended", "alert_sent_3day", "alert_sent_1day"]

class DetectedSubscriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetectedSubscription
        fields = ["id", "service_name", "amount", "billing_cycle", "next_renewal", "is_active"]
