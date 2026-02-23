"""Email intelligence views — inbox, purchases, webhooks."""
import hashlib
import hmac

from django.conf import settings
from django.db.models import Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.permissions import IsConnectedUser
from common.utils import error_response, success_response

from .models import (
    DetectedSubscription,
    InboxEmail,
    ParsedOrder,
    RefundTracking,
    ReturnWindow,
)
from .serializers import (
    DetectedSubscriptionSerializer,
    InboxEmailSerializer,
    ParsedOrderSerializer,
    RefundTrackingSerializer,
    ReturnWindowSerializer,
)


class InboxListView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        qs = InboxEmail.objects.filter(user=request.user, is_deleted=False).order_by("-received_at")

        category = request.query_params.get("category")
        unread = request.query_params.get("unread")
        starred = request.query_params.get("starred")

        if category:
            qs = qs.filter(category=category)
        if unread == "1":
            qs = qs.filter(is_read=False)
        if starred == "1":
            qs = qs.filter(is_starred=True)

        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(InboxEmailSerializer(page, many=True).data)
        return success_response(InboxEmailSerializer(qs, many=True).data)


class InboxDetailView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request, pk: str) -> Response:
        email = get_object_or_404(InboxEmail, pk=pk, user=request.user, is_deleted=False)
        # Mark as read
        if not email.is_read:
            InboxEmail.objects.filter(pk=pk).update(is_read=True)
        return success_response(InboxEmailSerializer(email).data)

    def patch(self, request: Request, pk: str) -> Response:
        email = get_object_or_404(InboxEmail, pk=pk, user=request.user, is_deleted=False)
        allowed = {"is_read", "is_starred"}
        update_fields = {k: v for k, v in request.data.items() if k in allowed}
        if not update_fields:
            return error_response("validation_error", "Only is_read and is_starred can be patched.")
        for field, value in update_fields.items():
            setattr(email, field, value)
        email.save(update_fields=list(update_fields.keys()))
        return success_response(InboxEmailSerializer(email).data)

    def delete(self, request: Request, pk: str) -> Response:
        email = get_object_or_404(InboxEmail, pk=pk, user=request.user, is_deleted=False)
        email.is_deleted = True
        email.deleted_at = timezone.now()
        email.save(update_fields=["is_deleted", "deleted_at"])
        return success_response({"detail": "Email deleted."})


class InboxReparseView(APIView):
    """POST /api/v1/inbox/:pk/reparse — re-trigger NLP parsing for an email."""
    permission_classes = [IsConnectedUser]

    def post(self, request: Request, pk: str) -> Response:
        email = get_object_or_404(InboxEmail, pk=pk, user=request.user, is_deleted=False)
        # Reset parse status so worker picks it up again
        InboxEmail.objects.filter(pk=pk).update(parse_status=InboxEmail.ParseStatus.PENDING)
        # TODO Sprint 3: enqueue email.parse_email Celery task
        return success_response({"detail": "Email queued for re-parsing."})


class PurchaseDashboardView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        user = request.user
        orders = ParsedOrder.objects.filter(user=user)
        total_orders = orders.count()
        total_spend = orders.aggregate(total=Sum("total_amount"))["total"] or 0

        active_return_windows = ReturnWindow.objects.filter(
            user=user, window_end_date__gte=timezone.now().date()
        ).count()

        pending_refunds = RefundTracking.objects.filter(
            user=user, status__in=["initiated", "processing"]
        ).count()

        active_subscriptions = DetectedSubscription.objects.filter(
            user=user, is_active=True
        ).count()

        return success_response({
            "total_orders": total_orders,
            "total_spend": str(total_spend),
            "active_return_windows": active_return_windows,
            "pending_refunds": pending_refunds,
            "active_subscriptions": active_subscriptions,
        })


class PurchaseListView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        qs = ParsedOrder.objects.filter(user=request.user).order_by("-order_date", "-created_at")

        marketplace = request.query_params.get("marketplace")
        if marketplace:
            qs = qs.filter(marketplace__iexact=marketplace)

        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(ParsedOrderSerializer(page, many=True).data)
        return success_response(ParsedOrderSerializer(qs, many=True).data)


class RefundsView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        qs = RefundTracking.objects.filter(user=request.user).order_by("-created_at")
        return success_response(RefundTrackingSerializer(qs, many=True).data)


class ReturnWindowsView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        qs = ReturnWindow.objects.filter(
            user=request.user, window_end_date__gte=timezone.now().date()
        ).order_by("window_end_date")
        return success_response(ReturnWindowSerializer(qs, many=True).data)


class SubscriptionsView(APIView):
    permission_classes = [IsConnectedUser]

    def get(self, request: Request) -> Response:
        qs = DetectedSubscription.objects.filter(user=request.user, is_active=True).order_by(
            "service_name"
        )
        return success_response(DetectedSubscriptionSerializer(qs, many=True).data)


class InboundEmailWebhookView(APIView):
    """Cloudflare Email Worker → Django. Validates HMAC-SHA256 signature."""
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        secret = getattr(settings, "CLOUDFLARE_EMAIL_WEBHOOK_SECRET", "")
        if secret:
            sig = request.headers.get("X-Webhook-Signature", "")
            body = request.body
            expected = hmac.new(
                secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return error_response("unauthorized", "Invalid webhook signature.", status=401)

        # TODO Sprint 3 Week 8: enqueue email.process_inbound_email Celery task
        # payload = request.data
        return Response({"ok": True}, status=202)


class RazorpayWebhookView(APIView):
    """Razorpay webhook — validates signature and routes event."""
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        secret = getattr(settings, "RAZORPAY_WEBHOOK_SECRET", "")
        if secret:
            sig = request.headers.get("X-Razorpay-Signature", "")
            body = request.body
            expected = hmac.new(
                secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return error_response("unauthorized", "Invalid webhook signature.", status=401)

        # TODO Sprint 4: handle payment.captured, subscription.activated events
        return Response({"ok": True}, status=200)
