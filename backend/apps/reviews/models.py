"""Review aggregation models.

PostgreSQL schema: public
"""
import uuid
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models


RATING_1_5 = [MinValueValidator(1), MaxValueValidator(5)]


class Review(models.Model):
    class Source(models.TextChoices):
        SCRAPED = "scraped", "Scraped"
        WHYDUD = "whydud", "Whydud"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        "products.ProductListing", on_delete=models.CASCADE, null=True, blank=True, related_name="reviews"
    )
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(
        "accounts.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="reviews"
    )
    source = models.CharField(max_length=20, choices=Source.choices, default=Source.SCRAPED)
    external_review_id = models.CharField(max_length=200, blank=True)
    reviewer_name = models.CharField(max_length=200, blank=True)
    rating = models.SmallIntegerField()
    title = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    body_positive = models.TextField(null=True, blank=True)
    body_negative = models.TextField(null=True, blank=True)
    nps_score = models.SmallIntegerField(
        null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(10)]
    )
    media = models.JSONField(default=list, blank=True)

    # Purchase proof (for Whydud-native reviews)
    has_purchase_proof = models.BooleanField(default=False)
    purchase_proof_url = models.CharField(max_length=500, null=True, blank=True)
    purchase_platform = models.CharField(max_length=50, null=True, blank=True)
    purchase_seller = models.CharField(max_length=200, null=True, blank=True)
    purchase_delivery_date = models.DateField(null=True, blank=True)
    purchase_price_paid = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_verified_purchase = models.BooleanField(default=False)

    # Feature ratings (category-specific)
    feature_ratings = models.JSONField(default=dict, blank=True)

    # Seller feedback
    seller_delivery_rating = models.SmallIntegerField(null=True, blank=True, validators=RATING_1_5)
    seller_packaging_rating = models.SmallIntegerField(null=True, blank=True, validators=RATING_1_5)
    seller_accuracy_rating = models.SmallIntegerField(null=True, blank=True, validators=RATING_1_5)
    seller_communication_rating = models.SmallIntegerField(null=True, blank=True, validators=RATING_1_5)

    review_date = models.DateField(null=True, blank=True)
    helpful_votes = models.IntegerField(default=0)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, blank=True)
    extracted_pros = models.JSONField(default=list)
    extracted_cons = models.JSONField(default=list)
    credibility_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    fraud_flags = models.JSONField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)
    is_published = models.BooleanField(default=True)
    publish_at = models.DateTimeField(null=True, blank=True)
    content_hash = models.CharField(max_length=64, blank=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    vote_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reviews"
        unique_together = [("listing", "external_review_id")]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["content_hash"]),
            models.Index(
                fields=["user"],
                condition=models.Q(user__isnull=False),
                name="idx_reviews_user",
            ),
            models.Index(fields=["source", "product"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name="rating_range"),
            models.UniqueConstraint(
                fields=["user", "product"],
                condition=models.Q(user__isnull=False),
                name="one_review_per_user_product",
            ),
        ]

    def __str__(self) -> str:
        return f"Review {self.id} — {self.rating}★"


class ReviewVote(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    review = models.ForeignKey(Review, on_delete=models.CASCADE, related_name="votes")
    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="review_votes")
    vote = models.SmallIntegerField()  # 1 or -1
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'users"."review_votes'
        unique_together = [("review", "user")]
        constraints = [
            models.CheckConstraint(check=models.Q(vote__in=[1, -1]), name="vote_value"),
        ]

    def __str__(self) -> str:
        return f"{self.user.email} {'▲' if self.vote == 1 else '▼'} review {self.review_id}"


class ReviewerProfile(models.Model):
    """Aggregated reviewer stats and gamification profile."""

    class Level(models.TextChoices):
        BRONZE = "bronze", "Bronze"
        SILVER = "silver", "Silver"
        GOLD = "gold", "Gold"
        PLATINUM = "platinum", "Platinum"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField("accounts.User", on_delete=models.CASCADE, related_name="reviewer_profile")
    total_reviews = models.IntegerField(default=0)
    total_upvotes_received = models.IntegerField(default=0)
    total_helpful_votes = models.IntegerField(default=0)
    review_quality_avg = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    reviewer_level = models.CharField(max_length=20, choices=Level.choices, default=Level.BRONZE)
    badges = models.JSONField(default=list, blank=True)
    leaderboard_rank = models.IntegerField(null=True, blank=True)
    is_top_reviewer = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'users"."reviewer_profiles'

    def __str__(self) -> str:
        return f"{self.user.email} — {self.reviewer_level} reviewer"
