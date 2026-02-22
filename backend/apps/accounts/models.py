"""User account models.

PostgreSQL schema: users
"""
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class UserManager(BaseUserManager):
    """Custom manager for User model using email as username."""

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email: str, password: str, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """Primary user account. Maps to users.accounts in PostgreSQL."""

    class Role(models.TextChoices):
        REGISTERED = "registered", "Registered"
        CONNECTED = "connected", "Connected"
        PREMIUM = "premium", "Premium"
        MODERATOR = "moderator", "Moderator"
        SENIOR_MOD = "senior_moderator", "Senior Moderator"
        DATA_OPS = "data_ops", "Data Ops"
        FRAUD_ANALYST = "fraud_analyst", "Fraud Analyst"
        TRUST_ENGINEER = "trust_engineer", "Trust Engineer"
        ADMIN = "admin", "Admin"
        SUPER_ADMIN = "super_admin", "Super Admin"

    class SubscriptionTier(models.TextChoices):
        FREE = "free", "Free"
        PREMIUM = "premium", "Premium"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    name = models.CharField(max_length=200, blank=True)
    avatar_url = models.URLField(max_length=500, blank=True)
    role = models.CharField(max_length=30, choices=Role.choices, default=Role.REGISTERED)
    subscription_tier = models.CharField(
        max_length=20, choices=SubscriptionTier.choices, default=SubscriptionTier.FREE
    )
    subscription_expires_at = models.DateTimeField(null=True, blank=True)
    has_whydud_email = models.BooleanField(default=False)
    trust_score = models.DecimalField(max_digits=3, decimal_places=2, default="0.50")
    is_suspended = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'users\".\"accounts'
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self) -> str:
        return self.email


class WhydudEmail(models.Model):
    """@whyd.xyz email address assigned to a user."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="whydud_email")
    username = models.CharField(max_length=30, unique=True)
    is_active = models.BooleanField(default=True)
    total_emails_received = models.IntegerField(default=0)
    total_orders_detected = models.IntegerField(default=0)
    last_email_received_at = models.DateTimeField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    marketplaces_registered = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users\".\"whydud_emails'

    @property
    def email_address(self) -> str:
        return f"{self.username}@whyd.xyz"

    def __str__(self) -> str:
        return self.email_address


class OAuthConnection(models.Model):
    """OAuth connections (Google Gmail, future providers)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="oauth_connections")
    provider = models.CharField(max_length=50)
    provider_user_id = models.CharField(max_length=200)
    # Stored encrypted (AES-256-GCM)
    access_token_encrypted = models.BinaryField(null=True, blank=True)
    refresh_token_encrypted = models.BinaryField(null=True, blank=True)
    token_expires_at = models.DateTimeField(null=True, blank=True)
    scopes = models.JSONField(default=list)
    connected_at = models.DateTimeField(auto_now_add=True)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="active")

    class Meta:
        db_table = 'users\".\"oauth_connections'
        unique_together = [("provider", "provider_user_id")]

    def __str__(self) -> str:
        return f"{self.user.email} — {self.provider}"


class PaymentMethod(models.Model):
    """Card vault — stores bank name + variant ONLY. No card numbers."""

    class MethodType(models.TextChoices):
        CREDIT_CARD = "credit_card", "Credit Card"
        DEBIT_CARD = "debit_card", "Debit Card"
        UPI = "upi", "UPI"
        WALLET = "wallet", "Wallet"
        MEMBERSHIP = "membership", "Membership"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payment_methods")
    method_type = models.CharField(max_length=20, choices=MethodType.choices)
    bank_name = models.CharField(max_length=100, blank=True)
    card_variant = models.CharField(max_length=200, blank=True)
    card_network = models.CharField(max_length=20, blank=True)
    wallet_provider = models.CharField(max_length=50, blank=True)
    wallet_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    upi_app = models.CharField(max_length=50, blank=True)
    upi_bank = models.CharField(max_length=100, blank=True)
    membership_type = models.CharField(max_length=50, blank=True)
    emi_eligible = models.BooleanField(default=False)
    nickname = models.CharField(max_length=100, blank=True)
    is_preferred = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users\".\"payment_methods'

    def __str__(self) -> str:
        return f"{self.user.email} — {self.method_type} {self.bank_name}"


class TCOProfile(models.Model):
    """User's TCO preferences (city, electricity tariff, usage habits)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="tco_profile")
    city_id = models.IntegerField(null=True, blank=True)
    electricity_tariff_override = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    ac_hours_per_day = models.SmallIntegerField(null=True, blank=True)
    ownership_years = models.SmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users\".\"tco_profiles'
