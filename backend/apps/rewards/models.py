import uuid
from django.db import models

class RewardPointsLedger(models.Model):
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="points_ledger")
    points = models.IntegerField()
    action_type = models.CharField(max_length=50)
    reference_type = models.CharField(max_length=50, blank=True)
    reference_id = models.UUIDField(null=True, blank=True)
    description = models.CharField(max_length=500, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."reward_points_ledger'
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user.email} {self.points:+d} pts ({self.action_type})"


class RewardBalance(models.Model):
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, primary_key=True, related_name="reward_balance")
    total_earned = models.IntegerField(default=0)
    total_spent = models.IntegerField(default=0)
    total_expired = models.IntegerField(default=0)
    current_balance = models.IntegerField(default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."reward_balances'


class GiftCardCatalog(models.Model):
    brand_name = models.CharField(max_length=200)
    brand_slug = models.CharField(max_length=100, unique=True)
    brand_logo_url = models.URLField(max_length=500, blank=True)
    denominations = models.JSONField()  # e.g. [100, 200, 500, 1000]
    category = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    fulfillment_partner = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."gift_card_catalog'

    def __str__(self) -> str:
        return self.brand_name


class GiftCardRedemption(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        FULFILLED = "fulfilled", "Fulfilled"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="gift_card_redemptions")
    catalog = models.ForeignKey(GiftCardCatalog, on_delete=models.PROTECT)
    denomination = models.DecimalField(max_digits=12, decimal_places=2)
    points_spent = models.IntegerField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.PENDING)
    gift_card_code = models.TextField(blank=True)  # encrypted
    delivery_email = models.EmailField(max_length=320, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."gift_card_redemptions'
