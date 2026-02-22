import uuid
from django.db import models

class Wishlist(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="wishlists")
    name = models.CharField(max_length=200, default="My Wishlist")
    is_default = models.BooleanField(default=False)
    is_public = models.BooleanField(default=False)
    share_slug = models.CharField(max_length=100, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."wishlists'

    def __str__(self) -> str:
        return f"{self.user.email} — {self.name}"


class WishlistItem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wishlist = models.ForeignKey(Wishlist, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    price_when_added = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    target_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    alert_enabled = models.BooleanField(default=True)
    last_alerted_at = models.DateTimeField(null=True, blank=True)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    price_change_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    lowest_since_added = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes = models.TextField(blank=True)
    priority = models.SmallIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."wishlist_items'
        unique_together = [("wishlist", "product")]
