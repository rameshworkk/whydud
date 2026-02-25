"""Serializers for the reviews app."""
from django.utils import timezone
from rest_framework import serializers

from .models import Review, ReviewerProfile, ReviewVote


class ReviewSerializer(serializers.ModelSerializer):
    user_vote = serializers.SerializerMethodField()
    marketplace_name = serializers.CharField(source="listing.marketplace.name", read_only=True)

    class Meta:
        model = Review
        fields = [
            "id", "marketplace_name", "reviewer_name", "rating",
            "title", "body", "is_verified_purchase", "review_date",
            "helpful_votes", "sentiment_score", "sentiment_label",
            "extracted_pros", "extracted_cons",
            "credibility_score", "is_flagged", "fraud_flags",
            "upvotes", "downvotes", "vote_score",
            "user_vote", "created_at",
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


class WriteReviewSerializer(serializers.ModelSerializer):
    """Validates and creates a Whydud-native review with 48hr publish hold."""

    feature_ratings = serializers.JSONField(required=False, default=dict)

    class Meta:
        model = Review
        fields = [
            "rating", "title", "body_positive", "body_negative",
            "nps_score", "feature_ratings",
            "purchase_platform", "purchase_seller",
            "purchase_delivery_date", "purchase_price_paid",
            "seller_delivery_rating", "seller_packaging_rating",
            "seller_accuracy_rating", "seller_communication_rating",
        ]

    def validate_rating(self, value: int) -> int:
        if not 1 <= value <= 5:
            raise serializers.ValidationError("Rating must be between 1 and 5.")
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

    def validate(self, attrs: dict) -> dict:
        user = self.context["request"].user
        product = self.context["product"]
        if Review.objects.filter(user=user, product=product).exists():
            raise serializers.ValidationError(
                {"non_field_errors": ["You have already reviewed this product."]}
            )
        return attrs

    def create(self, validated_data: dict) -> Review:
        user = self.context["request"].user
        product = self.context["product"]
        has_proof = bool(
            validated_data.get("purchase_platform")
            or validated_data.get("purchase_seller")
            or validated_data.get("purchase_price_paid")
        )
        review = Review.objects.create(
            **validated_data,
            user=user,
            product=product,
            reviewer_name=user.get_full_name() or user.email,
            source=Review.Source.WHYDUD,
            is_published=False,
            publish_at=timezone.now() + timezone.timedelta(hours=48),
            has_purchase_proof=has_proof,
            review_date=timezone.now().date(),
        )

        from apps.rewards.tasks import award_points_task
        award_points_task.delay(str(user.pk), 'write_review', str(review.pk))

        return review


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
