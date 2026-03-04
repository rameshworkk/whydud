"""User account models.

PostgreSQL schema: users
"""
import re
import secrets
import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import models


def validate_whydud_username_format(username: str) -> list[str]:
    """Validate @whyd.* username format rules (no DB queries).

    Returns a list of error messages (empty if valid).
    Rules:
      1. Length 3-30
      2. Only lowercase letters, digits, dots, underscores
      3. Must start with a letter
      4. No consecutive dots (..) or underscores (__)
      5. Cannot end with dot or underscore
    """
    if len(username) < 3 or len(username) > 30:
        return ["Username must be 3-30 characters"]
    if not re.fullmatch(r'[a-z0-9._]+', username):
        return ["Username can only contain lowercase letters, numbers, dots and underscores"]
    if not username[0].isalpha():
        return ["Username must start with a letter"]
    if '..' in username or '__' in username:
        return ["Username cannot contain consecutive dots or underscores"]
    if username[-1] in ('.', '_'):
        return ["Username cannot end with a dot or underscore"]
    return []


def _generate_referral_code() -> str:
    """Generate a unique 8-char uppercase referral code."""
    return secrets.token_hex(4).upper()  # 8 hex chars


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
    referral_code = models.CharField(max_length=8, unique=True, default=_generate_referral_code)
    referred_by = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="referrals"
    )
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
    """@whyd.* email address assigned to a user (whyd.in / whyd.click / whyd.shop)."""

    class Domain(models.TextChoices):
        WHYD_IN = "whyd.in", "whyd.in"
        WHYD_CLICK = "whyd.click", "whyd.click"
        WHYD_SHOP = "whyd.shop", "whyd.shop"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="whydud_email")
    username = models.CharField(max_length=30)
    domain = models.CharField(max_length=20, choices=Domain.choices, default=Domain.WHYD_IN)
    is_active = models.BooleanField(default=True)
    total_emails_received = models.IntegerField(default=0)
    total_orders_detected = models.IntegerField(default=0)
    last_email_received_at = models.DateTimeField(null=True, blank=True)
    onboarding_complete = models.BooleanField(default=False)
    marketplaces_registered = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users\".\"whydud_emails'
        unique_together = [("username", "domain")]

    @property
    def email_address(self) -> str:
        return f"{self.username}@{self.domain}"

    def clean(self) -> None:
        """Model-level username format validation (safety net)."""
        errors = validate_whydud_username_format(self.username or '')
        if errors:
            raise DjangoValidationError({'username': errors[0]})

    def __str__(self) -> str:
        return f"{self.username}@{self.domain}"


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


class ReservedUsername(models.Model):
    """Usernames that cannot be registered as @whyd.xyz addresses.

    Seeded via data migration with admin terms, brand names, and system words.
    """

    username = models.CharField(max_length=30, primary_key=True)

    class Meta:
        db_table = 'users"."reserved_usernames'

    def __str__(self) -> str:
        return self.username


def _pref_in_app_and_email():
    return {"in_app": True, "email": True}


def _pref_in_app_only():
    return {"in_app": True, "email": False}


class Notification(models.Model):
    """User notification — in-app and optionally emailed."""

    class Type(models.TextChoices):
        PRICE_DROP = "price_drop", "Price Drop"
        RETURN_WINDOW = "return_window", "Return Window"
        REFUND_DELAY = "refund_delay", "Refund Delay"
        BACK_IN_STOCK = "back_in_stock", "Back in Stock"
        REVIEW_UPVOTE = "review_upvote", "Review Upvote"
        PRICE_ALERT = "price_alert", "Price Alert"
        DISCUSSION_REPLY = "discussion_reply", "Discussion Reply"
        LEVEL_UP = "level_up", "Level Up"
        POINTS_EARNED = "points_earned", "Points Earned"
        SUBSCRIPTION_RENEWAL = "subscription_renewal", "Subscription Renewal"
        ORDER_DETECTED = "order_detected", "Order Detected"

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=50, choices=Type.choices)
    title = models.CharField(max_length=500)
    body = models.TextField(null=True, blank=True)
    action_url = models.CharField(max_length=500, null=True, blank=True)
    action_label = models.CharField(max_length=100, null=True, blank=True)
    entity_type = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=200, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    is_read = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    email_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."notifications'
        indexes = [
            models.Index(fields=["user", "-created_at"]),
            models.Index(
                fields=["user", "is_read"],
                condition=models.Q(is_read=False),
                name="idx_notif_unread",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.type}: {self.title}"


class NotificationPreference(models.Model):
    """Per-user notification channel preferences."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="notification_preferences")
    price_drops = models.JSONField(default=_pref_in_app_and_email)
    return_windows = models.JSONField(default=_pref_in_app_and_email)
    refund_delays = models.JSONField(default=_pref_in_app_and_email)
    back_in_stock = models.JSONField(default=_pref_in_app_only)
    review_upvotes = models.JSONField(default=_pref_in_app_only)
    price_alerts = models.JSONField(default=_pref_in_app_and_email)
    discussion_replies = models.JSONField(default=_pref_in_app_only)
    level_up = models.JSONField(default=_pref_in_app_only)
    points_earned = models.JSONField(default=_pref_in_app_only)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."notification_preferences'

    def __str__(self) -> str:
        return f"NotifPrefs for {self.user.email}"


class PurchasePreference(models.Model):
    """Per-category recommendation questionnaire answers."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="purchase_preferences")
    category = models.ForeignKey("products.Category", on_delete=models.CASCADE)
    preferences = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."purchase_preferences'
        unique_together = [("user", "category")]
        indexes = [
            models.Index(fields=["user"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} prefs for {self.category_id}"
