"""Serializers for the accounts app."""
from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from apps.tco.models import UserTCOProfile
from .models import (
    MarketplacePreference, OAuthConnection, PaymentMethod, ReservedUsername,
    User, WhydudEmail, validate_whydud_username_format,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "email", "email_verified", "name", "avatar_url", "role",
            "subscription_tier", "has_whydud_email", "deletion_requested_at",
            "created_at",
        ]
        read_only_fields = [
            "id", "email_verified", "role", "has_whydud_email",
            "deletion_requested_at", "created_at",
        ]


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=200, required=False)
    whydud_username = serializers.CharField(max_length=30, required=False)
    referral_code = serializers.CharField(max_length=8, required=False)

    def validate_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class WhydudEmailSerializer(serializers.ModelSerializer):
    email_address = serializers.SerializerMethodField()

    class Meta:
        model = WhydudEmail
        fields = [
            "id", "username", "domain", "email_address", "is_active",
            "total_emails_received", "total_orders_detected",
            "onboarding_complete", "marketplaces_registered", "created_at",
        ]
        read_only_fields = ["id", "email_address", "total_emails_received",
                           "total_orders_detected", "created_at"]

    def get_email_address(self, obj: WhydudEmail) -> str:
        return obj.email_address

    def validate_username(self, value: str) -> str:
        """Enforce @whyd.* username rules."""
        value = value.lower().strip()

        # Format rules (length, characters, start/end, no consecutive dots/underscores)
        errors = validate_whydud_username_format(value)
        if errors:
            raise serializers.ValidationError(errors[0])

        # Reserved usernames
        if ReservedUsername.objects.filter(username=value).exists():
            raise serializers.ValidationError("This username is reserved")

        # Uniqueness per (username, domain)
        domain = self.initial_data.get('domain', WhydudEmail.Domain.WHYD_IN)
        if WhydudEmail.objects.filter(username=value, domain=domain).exists():
            raise serializers.ValidationError("Username already taken")

        return value


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

    def validate_new_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8)

    def validate_new_password(self, value: str) -> str:
        try:
            password_validation.validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(e.messages)
        return value


class MarketplacePreferenceSerializer(serializers.ModelSerializer):
    """Serializer for user marketplace preferences.

    Accepts a list of marketplace IDs. Returns the same plus a full
    ``all_marketplaces`` list for the settings UI.
    """

    all_marketplaces = serializers.SerializerMethodField()

    class Meta:
        model = MarketplacePreference
        fields = ["preferred_marketplaces", "all_marketplaces", "updated_at"]
        read_only_fields = ["updated_at"]

    def get_all_marketplaces(self, obj: MarketplacePreference) -> list[dict]:
        from apps.products.models import Marketplace

        return list(
            Marketplace.objects.values("id", "slug", "name").order_by("name")
        )

    def validate_preferred_marketplaces(self, value: list[int]) -> list[int]:
        if not value:
            return value
        from apps.products.models import Marketplace

        existing_ids = set(Marketplace.objects.values_list("id", flat=True))
        invalid = [mid for mid in value if mid not in existing_ids]
        if invalid:
            raise serializers.ValidationError(
                f"Invalid marketplace IDs: {invalid}"
            )
        return sorted(set(value))


class DeleteAccountSerializer(serializers.Serializer):
    """Requires current password to confirm account deletion."""
    password = serializers.CharField(write_only=True)


class TCOProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserTCOProfile
        fields = [
            "city", "electricity_tariff_override",
            "ac_hours_per_day", "ownership_years",
        ]
