"""Notification views — list, read, dismiss, preferences."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import Notification, NotificationPreference
from .notification_serializers import (
    NotificationPreferenceSerializer,
    NotificationSerializer,
)


class NotificationListView(APIView):
    """GET /api/v1/notifications — paginated user notifications."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = Notification.objects.filter(user=request.user).order_by("-created_at")
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                NotificationSerializer(page, many=True).data
            )
        return success_response(NotificationSerializer(qs, many=True).data)


class UnreadCountView(APIView):
    """GET /api/v1/notifications/unread-count — count for bell badge."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
        return success_response({"count": count})


class MarkReadView(APIView):
    """PATCH /api/v1/notifications/:id/read — mark single notification read."""

    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: int) -> Response:
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )
        if not notification.is_read:
            notification.is_read = True
            notification.save(update_fields=["is_read"])
        return success_response(NotificationSerializer(notification).data)


class MarkAllReadView(APIView):
    """POST /api/v1/notifications/mark-all-read — bulk update."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        updated = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return success_response({"updated": updated})


class DismissView(APIView):
    """DELETE /api/v1/notifications/:id — dismiss notification."""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request, pk: int) -> Response:
        notification = get_object_or_404(
            Notification, pk=pk, user=request.user
        )
        notification.delete()
        return success_response({"detail": "Notification dismissed."})


class PreferencesView(APIView):
    """GET + PATCH /api/v1/notifications/preferences."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        return success_response(NotificationPreferenceSerializer(prefs).data)

    def patch(self, request: Request) -> Response:
        prefs, _ = NotificationPreference.objects.get_or_create(
            user=request.user
        )
        serializer = NotificationPreferenceSerializer(
            prefs, data=request.data, partial=True
        )
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)
