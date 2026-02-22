import uuid
from django.db import models

class Deal(models.Model):
    class DealType(models.TextChoices):
        ERROR_PRICE = "error_price", "Error Pricing"
        LOWEST_EVER = "lowest_ever", "Lowest Ever"
        GENUINE_DISCOUNT = "genuine_discount", "Genuine Discount"
        FLASH_SALE = "flash_sale", "Flash Sale"

    class Confidence(models.TextChoices):
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="deals")
    listing = models.ForeignKey("products.ProductListing", on_delete=models.SET_NULL, null=True, blank=True)
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.SET_NULL, null=True, blank=True)
    deal_type = models.CharField(max_length=30, choices=DealType.choices)
    current_price = models.DecimalField(max_digits=12, decimal_places=2)
    reference_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence = models.CharField(max_length=20, choices=Confidence.choices)
    is_active = models.BooleanField(default=True)
    detected_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    views = models.IntegerField(default=0)
    clicks = models.IntegerField(default=0)
    metadata = models.JSONField(null=True, blank=True)

    class Meta:
        db_table = "deals"
        indexes = [models.Index(fields=["is_active", "deal_type"])]

    def __str__(self) -> str:
        return f"{self.deal_type} — {self.product.title}"
