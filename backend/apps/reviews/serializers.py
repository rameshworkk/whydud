from rest_framework import serializers
from .models import Review, ReviewVote

class ReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = Review
        fields = [
            "id", "reviewer_name", "rating", "title", "body",
            "is_verified_purchase", "review_date", "helpful_votes",
            "sentiment_score", "sentiment_label",
            "extracted_pros", "extracted_cons",
            "credibility_score", "is_flagged",
            "upvotes", "downvotes", "vote_score",
        ]

class ReviewVoteSerializer(serializers.Serializer):
    vote = serializers.ChoiceField(choices=[1, -1])
