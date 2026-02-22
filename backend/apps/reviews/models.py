"""Review aggregation models.

PostgreSQL schema: public
"""
import uuid
from django.db import models

class Review(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey("products.ProductListing", on_delete=models.CASCADE, related_name="reviews")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="reviews")
    external_review_id = models.CharField(max_length=200, blank=True)
    reviewer_name = models.CharField(max_length=200, blank=True)
    rating = models.SmallIntegerField()
    title = models.CharField(max_length=500, blank=True)
    body = models.TextField(blank=True)
    is_verified_purchase = models.BooleanField(default=False)
    review_date = models.DateField(null=True, blank=True)
    helpful_votes = models.IntegerField(default=0)
    sentiment_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    sentiment_label = models.CharField(max_length=20, blank=True)
    extracted_pros = models.JSONField(default=list)
    extracted_cons = models.JSONField(default=list)
    credibility_score = models.DecimalField(max_digits=3, decimal_places=2, null=True, blank=True)
    fraud_flags = models.JSONField(null=True, blank=True)
    is_flagged = models.BooleanField(default=False)
    content_hash = models.CharField(max_length=64, blank=True)
    upvotes = models.IntegerField(default=0)
    downvotes = models.IntegerField(default=0)
    vote_score = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "reviews"
        unique_together = [("listing", "external_review_id")]
        indexes = [
            models.Index(fields=["product"]),
            models.Index(fields=["content_hash"]),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(rating__gte=1, rating__lte=5), name="rating_range"),
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
