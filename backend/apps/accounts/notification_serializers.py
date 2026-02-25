"""Serializers for notifications and notification preferences."""
from rest_framework import serializers

from .models import Notification, NotificationPreference


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            "id", "type", "title", "body",
            "action_url", "action_label",
            "is_read", "created_at",
        ]
        read_only_fields = fields


PREF_FIELDS = [
    "price_drops", "return_windows", "refund_delays",
    "back_in_stock", "review_upvotes", "price_alerts",
    "discussion_replies", "level_up", "points_earned",
]


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        fields = PREF_FIELDS

    def validate(self, attrs: dict) -> dict:
        for field, value in attrs.items():
            if not isinstance(value, dict):
                raise serializers.ValidationError(
                    {field: "Must be a JSON object with in_app/email keys."}
                )
            if set(value.keys()) - {"in_app", "email"}:
                raise serializers.ValidationError(
                    {field: "Only 'in_app' and 'email' keys are allowed."}
                )
            if not all(isinstance(v, bool) for v in value.values()):
                raise serializers.ValidationError(
                    {field: "Values must be booleans."}
                )
        return attrs
