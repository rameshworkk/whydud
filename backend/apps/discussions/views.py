"""Discussion views — threads, replies, votes."""
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import DiscussionReply, DiscussionThread, DiscussionVote
from .serializers import (
    DiscussionReplyCreateSerializer,
    DiscussionReplySerializer,
    DiscussionThreadSerializer,
)


class ThreadDetailView(APIView):
    """GET/PATCH/DELETE a single discussion thread."""
    permission_classes = [AllowAny]

    def get(self, request: Request, pk: str) -> Response:
        thread = get_object_or_404(DiscussionThread.objects.select_related("user"), pk=pk, is_removed=False)
        # Increment view count
        DiscussionThread.objects.filter(pk=pk).update(view_count=F("view_count") + 1)

        replies = thread.replies.filter(is_removed=False, parent_reply__isnull=True).select_related("user")
        return success_response({
            "thread": DiscussionThreadSerializer(thread, context={"request": request}).data,
            "replies": DiscussionReplySerializer(replies, many=True, context={"request": request}).data,
        })

    def patch(self, request: Request, pk: str) -> Response:
        if not request.user or not request.user.is_authenticated:
            return error_response("authentication_required", "Login required.", status=401)
        thread = get_object_or_404(DiscussionThread, pk=pk, is_removed=False)
        if thread.user != request.user and not request.user.is_staff:
            return error_response("forbidden", "You can only edit your own threads.", status=403)
        if thread.is_locked:
            return error_response("locked", "This thread is locked.")

        allowed_fields = {"title", "body"}
        data = {k: v for k, v in request.data.items() if k in allowed_fields}
        serializer = DiscussionThreadSerializer(thread, data=data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, pk: str) -> Response:
        if not request.user or not request.user.is_authenticated:
            return error_response("authentication_required", "Login required.", status=401)
        thread = get_object_or_404(DiscussionThread, pk=pk, is_removed=False)
        if thread.user != request.user and not request.user.is_staff:
            return error_response("forbidden", "You can only delete your own threads.", status=403)
        thread.is_removed = True
        thread.save(update_fields=["is_removed"])
        return success_response({"detail": "Thread removed."})


class ThreadReplyCreateView(APIView):
    """POST /api/v1/discussions/:pk/replies — add a reply."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: str) -> Response:
        thread = get_object_or_404(DiscussionThread, pk=pk, is_removed=False)
        if thread.is_locked:
            return error_response("locked", "This thread is locked.")

        serializer = DiscussionReplyCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        # Validate parent_reply belongs to same thread
        parent = serializer.validated_data.get("parent_reply")
        if parent and parent.thread != thread:
            return error_response("invalid_parent", "Parent reply does not belong to this thread.")

        reply = serializer.save(thread=thread, user=request.user)
        DiscussionThread.objects.filter(pk=pk).update(
            reply_count=F("reply_count") + 1,
            last_reply_at=reply.created_at,
        )
        return success_response(
            DiscussionReplySerializer(reply, context={"request": request}).data, status=201
        )


class ThreadVoteView(APIView):
    """POST /api/v1/discussions/:pk/vote — vote on a thread."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: str) -> Response:
        thread = get_object_or_404(DiscussionThread, pk=pk, is_removed=False)
        vote_value = request.data.get("vote")
        if vote_value not in (1, -1):
            return error_response("validation_error", "vote must be 1 or -1.")

        existing = DiscussionVote.objects.filter(
            user=request.user, target_type="thread", target_id=pk
        ).first()

        if existing:
            if existing.vote == vote_value:
                # Toggle off
                existing.delete()
                delta = -vote_value
                action = "removed"
            else:
                delta = vote_value - existing.vote
                existing.vote = vote_value
                existing.save(update_fields=["vote"])
                action = "changed"
        else:
            DiscussionVote.objects.create(
                user=request.user, target_type="thread", target_id=pk, vote=vote_value
            )
            delta = vote_value
            action = "cast"

        if delta > 0:
            DiscussionThread.objects.filter(pk=pk).update(upvotes=F("upvotes") + abs(delta))
        elif delta < 0:
            DiscussionThread.objects.filter(pk=pk).update(downvotes=F("downvotes") + abs(delta))

        return success_response({"action": action, "vote": vote_value if action != "removed" else None})


class ReplyVoteView(APIView):
    """POST /api/v1/discussions/replies/:pk/vote — vote on a reply."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: str) -> Response:
        reply = get_object_or_404(DiscussionReply, pk=pk, is_removed=False)
        vote_value = request.data.get("vote")
        if vote_value not in (1, -1):
            return error_response("validation_error", "vote must be 1 or -1.")

        existing = DiscussionVote.objects.filter(
            user=request.user, target_type="reply", target_id=pk
        ).first()

        if existing:
            if existing.vote == vote_value:
                existing.delete()
                delta = -vote_value
                action = "removed"
            else:
                delta = vote_value - existing.vote
                existing.vote = vote_value
                existing.save(update_fields=["vote"])
                action = "changed"
        else:
            DiscussionVote.objects.create(
                user=request.user, target_type="reply", target_id=pk, vote=vote_value
            )
            delta = vote_value
            action = "cast"

        if delta > 0:
            DiscussionReply.objects.filter(pk=pk).update(upvotes=F("upvotes") + abs(delta))
        elif delta < 0:
            DiscussionReply.objects.filter(pk=pk).update(downvotes=F("downvotes") + abs(delta))

        return success_response({"action": action, "vote": vote_value if action != "removed" else None})


class ReplyAcceptView(APIView):
    """POST /api/v1/discussions/replies/:pk/accept — mark as accepted answer."""
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: str) -> Response:
        reply = get_object_or_404(DiscussionReply, pk=pk, is_removed=False)
        thread = reply.thread

        # Only thread author can accept a reply
        if thread.user != request.user:
            return error_response("forbidden", "Only the thread author can accept a reply.", status=403)

        # Unaccept any currently accepted reply in this thread
        DiscussionReply.objects.filter(thread=thread, is_accepted=True).update(is_accepted=False)
        reply.is_accepted = True
        reply.save(update_fields=["is_accepted"])

        return success_response(
            DiscussionReplySerializer(reply, context={"request": request}).data
        )
