"""Serializers for the discussions app."""
from rest_framework import serializers

from .models import DiscussionReply, DiscussionThread, DiscussionVote


class DiscussionAuthorSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    avatar_url = serializers.URLField(allow_null=True)


class DiscussionReplySerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionReply
        fields = [
            "id", "thread", "parent_reply", "body",
            "upvotes", "downvotes", "is_accepted",
            "author", "user_vote", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "upvotes", "downvotes", "created_at", "updated_at"]

    def get_author(self, obj: DiscussionReply) -> dict:
        return {"id": str(obj.user.pk), "name": obj.user.name or obj.user.email, "avatar_url": obj.user.avatar_url}

    def get_user_vote(self, obj: DiscussionReply) -> int | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = DiscussionVote.objects.get(user=request.user, target_type="reply", target_id=obj.pk)
            return vote.vote
        except DiscussionVote.DoesNotExist:
            return None


class DiscussionThreadSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    user_vote = serializers.SerializerMethodField()

    class Meta:
        model = DiscussionThread
        fields = [
            "id", "product", "thread_type", "title", "body",
            "reply_count", "upvotes", "downvotes", "view_count",
            "is_pinned", "is_locked", "last_reply_at",
            "author", "user_vote", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "product", "reply_count", "upvotes", "downvotes",
            "view_count", "is_pinned", "is_locked", "last_reply_at",
            "created_at", "updated_at",
        ]

    def get_author(self, obj: DiscussionThread) -> dict:
        return {"id": str(obj.user.pk), "name": obj.user.name or obj.user.email, "avatar_url": obj.user.avatar_url}

    def get_user_vote(self, obj: DiscussionThread) -> int | None:
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        try:
            vote = DiscussionVote.objects.get(user=request.user, target_type="thread", target_id=obj.pk)
            return vote.vote
        except DiscussionVote.DoesNotExist:
            return None


class DiscussionThreadCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionThread
        fields = ["thread_type", "title", "body"]


class DiscussionReplyCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionReply
        fields = ["body", "parent_reply"]
