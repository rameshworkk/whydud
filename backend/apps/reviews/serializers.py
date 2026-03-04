"""Serializers for the reviews app."""
from rest_framework import serializers

from .models import Review, ReviewerProfile, ReviewVote


class ReviewSerializer(serializers.ModelSerializer):
    user_vote = serializers.SerializerMethodField()
    marketplace_name = serializers.SerializerMethodField()
    marketplace_slug = serializers.CharField(source="marketplace.slug", read_only=True, default=None)
    external_reviewer_name = serializers.CharField(read_only=True)
    helpful_vote_count = serializers.IntegerField(read_only=True)
    variant_info = serializers.CharField(read_only=True)
    external_review_url = serializers.URLField(read_only=True)
    is_scraped = serializers.SerializerMethodField()
    media = serializers.JSONField(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "marketplace_name", "marketplace_slug",
            "reviewer_name", "external_reviewer_name",
            "rating", "title", "body",
            "is_verified_purchase", "review_date",
            "helpful_votes", "helpful_vote_count",
            "sentiment_score", "sentiment_label",
            "extracted_pros", "extracted_cons",
            "credibility_score", "is_flagged", "fraud_flags",
            "upvotes", "downvotes", "vote_score",
            "user_vote", "is_scraped",
            "variant_info", "external_review_url", "media",
            "created_at",
        ]

    def get_user_vote(self, obj: Review) -> int | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = obj.votes.get(user=request.user)
            return vote.vote
        except ReviewVote.DoesNotExist:
            return None

    def get_marketplace_name(self, obj: Review) -> str | None:
        if obj.marketplace:
            return obj.marketplace.name
        if obj.listing and obj.listing.marketplace:
            return obj.listing.marketplace.name
        return None

    def get_is_scraped(self, obj: Review) -> bool:
        return obj.source == Review.Source.SCRAPED and obj.user is None


class WriteReviewSerializer(serializers.ModelSerializer):
    """Validates and creates a Whydud-native review with 48hr publish hold.

    Accepts all four tabs of the review form as a single POST:
      Tab 1: Purchase verification (optional)
      Tab 2: Review content (rating + title required)
      Tab 3: Feature ratings (optional, category-specific)
      Tab 4: Seller feedback (optional)
    """

    feature_ratings = serializers.JSONField(required=False, default=dict)
    media = serializers.JSONField(required=False, default=list)
    has_purchase_proof = serializers.BooleanField(required=False, default=False)
    purchase_proof_url = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )

    class Meta:
        model = Review
        fields = [
            # Tab 1: Verify Purchase
            "has_purchase_proof", "purchase_proof_url",
            "purchase_platform", "purchase_seller",
            "purchase_delivery_date", "purchase_price_paid",
            # Tab 2: Leave a Review
            "rating", "title", "body_positive", "body_negative",
            "media", "nps_score",
            # Tab 3: Rate Features
            "feature_ratings",
            # Tab 4: Seller Feedback
            "seller_delivery_rating", "seller_packaging_rating",
            "seller_accuracy_rating", "seller_communication_rating",
        ]

    def validate_rating(self, value: int) -> int:
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
        return value

    def validate_title(self, value: str) -> str:
        if len(value) < 5:
            raise serializers.ValidationError("Title must be at least 5 characters.")
        if len(value) > 200:
            raise serializers.ValidationError("Title must be at most 200 characters.")
        return value

    def validate_purchase_price_paid(self, value):
        if value is not None and value <= 0:
            raise serializers.ValidationError("Price paid must be greater than 0.")
        return value

    def validate_feature_ratings(self, value: dict) -> dict:
        if not isinstance(value, dict):
            raise serializers.ValidationError("feature_ratings must be a JSON object.")
        for key, rating in value.items():
            if not isinstance(key, str):
                raise serializers.ValidationError("Feature keys must be strings.")
            if not isinstance(rating, (int, float)) or not 1 <= rating <= 5:
                raise serializers.ValidationError(
                    f"Feature rating '{key}' must be between 1 and 5."
                )
        return value

    def validate_media(self, value: list) -> list:
        if not isinstance(value, list):
            raise serializers.ValidationError("media must be a JSON array.")
        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError("Each media item must be an object.")
            if "url" not in item or "type" not in item:
                raise serializers.ValidationError(
                    "Each media item must have 'url' and 'type' fields."
                )
            if item["type"] not in ("image", "video"):
                raise serializers.ValidationError(
                    "Media type must be 'image' or 'video'."
                )
        return value

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        product = self.context["product"]
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["You have already reviewed this product."]}
            )
        return attrs

    def create(self, validated_data: dict) -> Review:
        from .services import create_review

        user = self.context["request"].user
        product = self.context["product"]
        return create_review(user, product, validated_data)


class MyReviewsSerializer(serializers.ModelSerializer):
    """List serializer for a user's own reviews."""

    product_name = serializers.CharField(source="product.name", read_only=True)
    product_slug = serializers.CharField(source="product.slug", read_only=True)
    product_image = serializers.SerializerMethodField()

    class Meta:
        model = Review
        fields = [
            "id", "product_name", "product_slug", "product_image",
            "rating", "title", "body_positive", "body_negative",
            "nps_score", "feature_ratings",
            "seller_delivery_rating", "seller_packaging_rating",
            "seller_accuracy_rating", "seller_communication_rating",
            "has_purchase_proof", "is_published", "publish_at",
            "upvotes", "downvotes", "vote_score",
            "created_at", "updated_at",
        ]

    def get_product_image(self, obj: Review) -> str | None:
        product = obj.product
        if product.images and len(product.images) > 0:
            return product.images[0]
        return None


class ReviewerProfileSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = ReviewerProfile
        fields = [
            "user_name", "total_reviews", "total_upvotes_received",
            "total_helpful_votes", "review_quality_avg",
            "reviewer_level", "badges", "leaderboard_rank",
            "is_top_reviewer",
        ]
        read_only_fields = fields


class ReviewVoteSerializer(serializers.Serializer):
    vote = serializers.ChoiceField(choices=[1, -1])
