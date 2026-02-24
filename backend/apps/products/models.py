"""Product catalogue models.

PostgreSQL schema: public
"""
import uuid

from django.db import models


class Marketplace(models.Model):
    """Supported marketplaces (Amazon.in, Flipkart, etc.)."""

    slug = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    base_url = models.URLField(max_length=500)
    affiliate_tag = models.CharField(max_length=100, blank=True)
    affiliate_param = models.CharField(max_length=50, blank=True)
    scraper_status = models.CharField(max_length=20, default="active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "marketplaces"

    def __str__(self) -> str:
        return self.name


class Category(models.Model):
    """Hierarchical product categories with optional TCO support."""

    slug = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    parent = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="children"
    )
    spec_schema = models.JSONField(null=True, blank=True)
    level = models.SmallIntegerField(default=0)
    has_tco_model = models.BooleanField(default=False)
    product_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "categories"
        verbose_name_plural = "Categories"

    def __str__(self) -> str:
        return self.name


class Brand(models.Model):
    """Product brand registry."""

    slug = models.CharField(max_length=100, unique=True)
    name = models.CharField(max_length=200)
    aliases = models.JSONField(default=list)
    verified = models.BooleanField(default=False)
    logo_url = models.URLField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "brands"

    def __str__(self) -> str:
        return self.name


class Product(models.Model):
    """Canonical product — aggregated across all marketplaces."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        DISCONTINUED = "discontinued", "Discontinued"
        PENDING = "pending", "Pending Review"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    slug = models.CharField(max_length=500, unique=True)
    title = models.CharField(max_length=1000)
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, related_name="products")
    description = models.TextField(blank=True)
    specs = models.JSONField(null=True, blank=True)
    images = models.JSONField(null=True, blank=True)

    dud_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    dud_score_confidence = models.CharField(max_length=20, blank=True)
    dud_score_updated_at = models.DateTimeField(null=True, blank=True)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    total_reviews = models.IntegerField(default=0)
    lowest_price_ever = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    lowest_price_date = models.DateField(null=True, blank=True)
    current_best_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    current_best_marketplace = models.CharField(max_length=50, blank=True)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    merged_into = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="merged_from"
    )
    is_refurbished = models.BooleanField(default=False)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "products"
        indexes = [
            models.Index(fields=["brand"]),
            models.Index(fields=["category"]),
            models.Index(fields=["-dud_score"]),
        ]

    def __str__(self) -> str:
        return self.title


class Seller(models.Model):
    """Marketplace seller profiles."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE, related_name="sellers")
    external_seller_id = models.CharField(max_length=200, blank=True)
    name = models.CharField(max_length=500)
    avg_rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    total_ratings = models.IntegerField(default=0)
    positive_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    ships_from = models.CharField(max_length=200, blank=True)
    fulfilled_by = models.CharField(max_length=100, blank=True)
    is_verified = models.BooleanField(default=False)
    seller_since = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sellers"
        unique_together = [("marketplace", "external_seller_id")]

    def __str__(self) -> str:
        return f"{self.name} ({self.marketplace.slug})"


class ProductListing(models.Model):
    """A product listed on a specific marketplace by a specific seller."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="listings")
    marketplace = models.ForeignKey(Marketplace, on_delete=models.CASCADE)
    seller = models.ForeignKey(Seller, on_delete=models.SET_NULL, null=True, blank=True)
    external_id = models.CharField(max_length=200)
    external_url = models.URLField(max_length=2000)
    affiliate_url = models.URLField(max_length=2000, blank=True)
    title = models.CharField(max_length=1000, blank=True)
    current_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    mrp = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    discount_pct = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    in_stock = models.BooleanField(default=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    review_count = models.IntegerField(default=0)
    match_confidence = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    match_method = models.CharField(max_length=50, blank=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "product_listings"
        unique_together = [("marketplace", "external_id")]
        indexes = [models.Index(fields=["product"])]

    def __str__(self) -> str:
        return f"{self.product.title} on {self.marketplace.slug}"


class BankCard(models.Model):
    """Reference data: bank cards available in India."""

    bank_slug = models.CharField(max_length=50)
    bank_name = models.CharField(max_length=100)
    card_variant = models.CharField(max_length=200)
    card_type = models.CharField(max_length=20)
    card_network = models.CharField(max_length=20, blank=True)
    is_co_branded = models.BooleanField(default=False)
    co_brand_partner = models.CharField(max_length=50, blank=True)
    default_cashback_pct = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    logo_url = models.URLField(max_length=500, blank=True)

    class Meta:
        db_table = "bank_cards"
        unique_together = [("bank_slug", "card_variant", "card_type")]

    def __str__(self) -> str:
        return f"{self.bank_name} {self.card_variant}"


class CompareSession(models.Model):
    """Tracks which products a user is comparing (persisted across sessions)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="compare_sessions"
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    product_ids = models.JSONField(default=list)  # array of 2-4 product UUIDs
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."compare_sessions'

    def __str__(self) -> str:
        return f"Compare {self.id} ({len(self.product_ids)} products)"


class RecentlyViewed(models.Model):
    """Recently viewed products — per user or anonymous session."""

    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, null=True, blank=True, related_name="recently_viewed"
    )
    session_id = models.CharField(max_length=100, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="recent_views")
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."recently_viewed'
        indexes = [
            models.Index(fields=["user", "-viewed_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.user_id or self.session_id} viewed {self.product_id}"


class StockAlert(models.Model):
    """Back-in-stock notification request."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="stock_alerts")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_alerts")
    listing = models.ForeignKey(ProductListing, on_delete=models.SET_NULL, null=True, blank=True, related_name="stock_alerts")
    is_active = models.BooleanField(default=True)
    notified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."stock_alerts'
        unique_together = [("user", "product", "listing")]

    def __str__(self) -> str:
        return f"Stock alert: {self.user_id} → {self.product_id}"


class CategoryPreferenceSchema(models.Model):
    """UI schema defining the recommendation questionnaire per category."""

    category = models.OneToOneField(Category, on_delete=models.CASCADE, related_name="preference_schema")
    schema = models.JSONField()
    version = models.IntegerField(default=1)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "category_preference_schemas"

    def __str__(self) -> str:
        return f"{self.category.name} schema v{self.version}"
