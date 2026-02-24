"""Serializers for the accounts app."""
from rest_framework import serializers

from apps.tco.models import UserTCOProfile
from .models import OAuthConnection, PaymentMethod, User, WhydudEmail


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "email_verified", "name", "avatar_url", "role",
            "subscription_tier", "has_whydud_email", "created_at",
        ]
        read_only_fields = ["id", "email_verified", "role", "has_whydud_email", "created_at"]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=200, required=False)
    whydud_username = serializers.CharField(max_length=30, required=False)


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class WhydudEmailSerializer(serializers.ModelSerializer):
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = WhydudEmail
        fields = [
            "id", "username", "email_address", "is_active",
            "total_emails_received", "total_orders_detected",
            "onboarding_complete", "marketplaces_registered", "created_at",
        ]
        read_only_fields = ["id", "email_address", "total_emails_received",
                           "total_orders_detected", "created_at"]

    def get_email_address(self, obj: WhydudEmail) -> str:
        return obj.email_address


class PaymentMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaymentMethod
        fields = [
            "id", "method_type", "bank_name", "card_variant", "card_network",
            "wallet_provider", "upi_app", "upi_bank", "membership_type",
            "emi_eligible", "nickname", "is_preferred", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)


class TCOProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTCOProfile
        fields = [
            "city", "electricity_tariff_override",
            "ac_hours_per_day", "ownership_years",
        ]
