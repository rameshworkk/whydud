"""Email intelligence models — ISOLATED schema.

PostgreSQL schema: email_intel
Raw email bodies stored encrypted (AES-256-GCM).
"""
import uuid
from django.db import models

class InboxEmail(models.Model):
    class Category(models.TextChoices):
        ORDER = "order", "Order"
        SHIPPING = "shipping", "Shipping"
        REFUND = "refund", "Refund"
        RETURN = "return", "Return"
        SUBSCRIPTION = "subscription", "Subscription"
        PROMO = "promo", "Promotional"
        OTHER = "other", "Other"

    class ParseStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PARSED = "parsed", "Parsed"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="inbox_emails")
    whydud_email = models.ForeignKey(
        "accounts.WhydudEmail", on_delete=models.SET_NULL, null=True, blank=True
    )
    message_id = models.CharField(max_length=500, unique=True)
    sender_address = models.EmailField(max_length=320)
    sender_name = models.CharField(max_length=200, blank=True)
    subject = models.CharField(max_length=1000, blank=True)
    received_at = models.DateTimeField()
    # Body stored encrypted — decrypt only on explicit user request
    body_text_encrypted = models.BinaryField(null=True, blank=True)
    body_html_encrypted = models.BinaryField(null=True, blank=True)
    raw_size_bytes = models.IntegerField(null=True, blank=True)
    has_attachments = models.BooleanField(default=False)
    category = models.CharField(max_length=30, choices=Category.choices, blank=True)
    marketplace = models.CharField(max_length=50, blank=True)
    confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    parse_status = models.CharField(max_length=20, choices=ParseStatus.choices, default=ParseStatus.PENDING)
    parsed_entity_type = models.CharField(max_length=30, blank=True)
    parsed_entity_id = models.UUIDField(null=True, blank=True)
    is_read = models.BooleanField(default=False)
    is_starred = models.BooleanField(default=False)
    is_deleted = models.BooleanField(default=False)
    deleted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_intel"."inbox_emails'
        indexes = [
            models.Index(fields=["user", "-received_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.sender_address}: {self.subject}"


class ParsedOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="parsed_orders")
    source = models.CharField(max_length=20, default="whydud_email")  # whydud_email | gmail
    order_id = models.CharField(max_length=200, blank=True)
    marketplace = models.CharField(max_length=50)
    product_name = models.CharField(max_length=1000)
    quantity = models.SmallIntegerField(default=1)
    price_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    tax = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    shipping_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    order_date = models.DateField(null=True, blank=True)
    delivery_date = models.DateField(null=True, blank=True)
    seller_name = models.CharField(max_length=500, blank=True)
    payment_method = models.CharField(max_length=100, blank=True)
    matched_product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    match_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    match_status = models.CharField(max_length=20, default="pending")
    email_message_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_intel"."parsed_orders'
        unique_together = [("user", "email_message_id")]

    def __str__(self) -> str:
        return f"{self.order_id or 'order'} from {self.marketplace} ({self.order_date})"


class RefundTracking(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    order = models.ForeignKey(ParsedOrder, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=30)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    initiated_at = models.DateTimeField(null=True, blank=True)
    expected_by = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    marketplace = models.CharField(max_length=50, blank=True)
    delay_days = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_intel"."refund_tracking'

    def __str__(self) -> str:
        return f"Refund {self.status} — {self.marketplace} ({self.refund_amount})"


class ReturnWindow(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    order = models.ForeignKey(ParsedOrder, on_delete=models.SET_NULL, null=True, blank=True)
    window_end_date = models.DateField()
    is_extended = models.BooleanField(default=False)
    alert_sent_3day = models.BooleanField(default=False)
    alert_sent_1day = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'email_intel"."return_windows'

    def __str__(self) -> str:
        return f"Return window ends {self.window_end_date} (order={self.order_id})"


class DetectedSubscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE)
    service_name = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, default="INR")
    billing_cycle = models.CharField(max_length=20, blank=True)
    next_renewal = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'email_intel"."subscriptions'

    def __str__(self) -> str:
        return f"{self.service_name} ({self.billing_cycle}) — ₹{self.amount}"
