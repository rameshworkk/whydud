"""Pricing models: snapshots, offers, wishlists price alerts.

PostgreSQL schema: public (price_snapshots hypertable via TimescaleDB)
"""
import uuid
from django.db import models


class PriceSnapshot(models.Model):
    """TimescaleDB hypertable — one row per price check per listing.
    
    NOTE: Create hypertable manually after migration:
      SELECT create_hypertable('price_snapshots', 'time');
    """
    # No auto pk — TimescaleDB hypertable uses composite key (time, listing_id)
    time = models.DateTimeField()
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.CASCADE, db_column="listing_id"
    )
    product = models.ForeignKey(
        "products.Product", on_delete=models.CASCADE, db_column="product_id"
    )
    marketplace = models.ForeignKey(
        "products.Marketplace", on_delete=models.CASCADE, db_column="marketplace_id"
    )
    price = models.DecimalField(max_digits=12, decimal_places=2)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(null=True)
    seller_name = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "price_snapshots"
        managed = False  # TimescaleDB manages this table


class MarketplaceOffer(models.Model):
    """Bank/card offers scraped from marketplace pages."""

    class DiscountType(models.TextChoices):
        FLAT = "flat", "Flat Off"
        PERCENT = "percent", "Percent Off"
        CASHBACK = "cashback", "Cashback"
        NO_COST_EMI = "no_cost_emi", "No Cost EMI"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.CASCADE)
    scope_type = models.CharField(max_length=20)  # product, listing, category, sitewide
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, null=True, blank=True
    )
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.SET_NULL, null=True, blank=True
    )
    category = models.ForeignKey(
        "products.Category", on_delete=models.SET_NULL, null=True, blank=True
    )
    offer_type = models.CharField(max_length=30)
    title = models.CharField(max_length=500)
    description = models.TextField(blank=True)
    bank_slug = models.CharField(max_length=50, blank=True)
    card_type = models.CharField(max_length=20, blank=True)
    card_network = models.CharField(max_length=20, blank=True)
    card_variants = models.JSONField(default=list)
    wallet_provider = models.CharField(max_length=50, blank=True)
    membership_type = models.CharField(max_length=50, blank=True)
    coupon_code = models.CharField(max_length=100, blank=True)
    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    discount_value = models.DecimalField(max_digits=8, decimal_places=2)
    max_discount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    min_purchase = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    emi_tenures = models.JSONField(default=list)
    emi_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    emi_processing_fee = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    stackable = models.BooleanField(default=False)
    source = models.CharField(max_length=30)
    last_verified_at = models.DateTimeField(null=True, blank=True)
    terms_conditions = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplace_offers"
        indexes = [
            models.Index(fields=["marketplace", "is_active"]),
            models.Index(fields=["bank_slug"]),
        ]

    def __str__(self) -> str:
        return self.title


class PriceAlert(models.Model):
    """User price drop alert for a wishlist item."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="price_alerts")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    target_price = models.DecimalField(max_digits=12, decimal_places=2)
    is_active = models.BooleanField(default=True)
    last_alerted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "price_alerts"
        unique_together = [("user", "product")]

    def __str__(self) -> str:
        return f"{self.user.email} alert on {self.product_id} @ ₹{self.target_price}"
