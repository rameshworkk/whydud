from rest_framework import serializers
from .models import DiscussionReply, DiscussionThread

class DiscussionReplySerializer(serializers.ModelSerializer):
    class Meta:
        model = DiscussionReply
        fields = ["id", "user", "parent_reply", "body", "upvotes", "downvotes", "is_accepted", "created_at"]
        read_only_fields = ["id", "user", "upvotes", "downvotes", "created_at"]

class DiscussionThreadSerializer(serializers.ModelSerializer):
    replies = DiscussionReplySerializer(many=True, read_only=True)
    class Meta:
        model = DiscussionThread
        fields = [
            "id", "thread_type", "title", "body",
            "reply_count", "upvotes", "downvotes", "view_count",
            "is_pinned", "is_locked", "last_reply_at", "created_at",
            "replies",
        ]
        read_only_fields = ["id", "reply_count", "upvotes", "downvotes", "view_count",
                           "is_pinned", "is_locked", "last_reply_at", "created_at"]
