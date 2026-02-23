"""Serializers for the reviews app."""
from rest_framework import serializers

from .models import Review, ReviewVote


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


class ReviewVoteSerializer(serializers.Serializer):
    vote = serializers.ChoiceField(choices=[1, -1])
