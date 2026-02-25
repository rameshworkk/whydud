"""Email intelligence views — inbox, purchases, webhooks."""
import hashlib
import hmac
import logging
import uuid

from django.conf import settings
from django.db.models import Sum, Count, F
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import WhydudEmail
from common.encryption import encrypt
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
    ReplyEmailSerializer,
    ReturnWindowSerializer,
    SendEmailSerializer,
)
from .send_service import SendEmailError, send_email
from .tasks import process_inbound_email

logger = logging.getLogger(__name__)


class InboxListView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        email = get_object_or_404(InboxEmail, pk=pk, user=request.user, is_deleted=False)
        # Reset parse status so worker picks it up again
        InboxEmail.objects.filter(pk=pk).update(parse_status=InboxEmail.ParseStatus.PENDING)
        # TODO Sprint 3: enqueue email.parse_email Celery task
        return success_response({"detail": "Email queued for re-parsing."})


class PurchaseDashboardView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        orders = ParsedOrder.objects.filter(user=user)
        total_orders = orders.count()
        total_spent = orders.aggregate(total=Sum("total_amount"))["total"] or 0
        average_order_value = (total_spent / total_orders) if total_orders > 0 else 0

        # Top marketplace by order count
        top_mp = (
            orders.values("marketplace")
            .annotate(cnt=Count("id"))
            .order_by("-cnt")
            .first()
        )
        top_marketplace = top_mp["marketplace"] if top_mp else None

        # Monthly spending (last 6 months)
        monthly_spending = list(
            orders.filter(order_date__isnull=False)
            .annotate(month=TruncMonth("order_date"))
            .values("month")
            .annotate(amount=Sum("total_amount"))
            .order_by("month")[:6]
        )
        monthly_spending_out = [
            {"month": row["month"].strftime("%b %Y"), "amount": float(row["amount"])}
            for row in monthly_spending
        ]

        # Category breakdown (from marketplace field as proxy for now)
        category_breakdown = list(
            orders.values(category=F("marketplace"))
            .annotate(amount=Sum("total_amount"), count=Count("id"))
            .order_by("-amount")
        )
        category_breakdown_out = [
            {"category": row["category"] or "Other", "amount": float(row["amount"]), "count": row["count"]}
            for row in category_breakdown
        ]

        active_refunds = RefundTracking.objects.filter(
            user=user, status__in=["initiated", "processing"]
        ).count()

        expiring_returns = ReturnWindow.objects.filter(
            user=user, window_end_date__gte=timezone.now().date()
        ).count()

        active_subscriptions = DetectedSubscription.objects.filter(
            user=user, is_active=True
        ).count()

        return success_response({
            "total_spent": str(total_spent),
            "total_orders": total_orders,
            "average_order_value": str(average_order_value),
            "top_marketplace": top_marketplace,
            "monthly_spending": monthly_spending_out,
            "category_breakdown": category_breakdown_out,
            "active_refunds": active_refunds,
            "expiring_returns": expiring_returns,
            "active_subscriptions": active_subscriptions,
        })


class PurchaseListView(APIView):
    permission_classes = [IsAuthenticated]

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
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = RefundTracking.objects.filter(user=request.user).order_by("-created_at")
        return success_response(RefundTrackingSerializer(qs, many=True).data)


class ReturnWindowsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = ReturnWindow.objects.filter(
            user=request.user, window_end_date__gte=timezone.now().date()
        ).order_by("window_end_date")
        return success_response(ReturnWindowSerializer(qs, many=True).data)


class SubscriptionsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = DetectedSubscription.objects.filter(user=request.user, is_active=True).order_by(
            "service_name"
        )
        return success_response(DetectedSubscriptionSerializer(qs, many=True).data)


class SendEmailView(APIView):
    """POST /api/v1/inbox/send — compose and send a new email from @whyd.* address."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = SendEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        try:
            result = send_email(
                from_user_id=str(request.user.id),
                to_address=serializer.validated_data["to"],
                subject=serializer.validated_data["subject"],
                body_html=serializer.validated_data["body_html"],
                body_text=serializer.validated_data.get("body_text") or None,
            )
        except SendEmailError as exc:
            status_map = {
                "no_whydud_email": 400,
                "rate_limit_exceeded": 429,
                "invalid_recipient": 400,
                "config_error": 503,
                "send_failed": 502,
            }
            return error_response(exc.code, exc.message, status=status_map.get(exc.code, 400))

        return success_response({
            "email_id": result.inbox_email_id,
            "resend_message_id": result.resend_message_id,
        }, status=201)


class ReplyEmailView(APIView):
    """POST /api/v1/inbox/:id/reply — reply to an existing inbound email."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        # Fetch the original email being replied to
        original = get_object_or_404(
            InboxEmail, pk=pk, user=request.user, is_deleted=False
        )

        serializer = ReplyEmailSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        # Reply goes back to the original sender
        reply_to_address = original.sender_address
        reply_subject = original.subject
        if not reply_subject.lower().startswith("re:"):
            reply_subject = f"Re: {reply_subject}"

        try:
            result = send_email(
                from_user_id=str(request.user.id),
                to_address=reply_to_address,
                subject=reply_subject,
                body_html=serializer.validated_data["body_html"],
                body_text=serializer.validated_data.get("body_text") or None,
                reply_to_message_id=original.message_id,
            )
        except SendEmailError as exc:
            status_map = {
                "no_whydud_email": 400,
                "rate_limit_exceeded": 429,
                "invalid_recipient": 400,
                "config_error": 503,
                "send_failed": 502,
            }
            return error_response(exc.code, exc.message, status=status_map.get(exc.code, 400))

        return success_response({
            "email_id": result.inbox_email_id,
            "resend_message_id": result.resend_message_id,
        }, status=201)


class InboundEmailWebhookView(APIView):
    """Cloudflare Email Worker → Django. Validates HMAC-SHA256 signature.

    Expected payload from CF Email Worker:
        to          — full recipient address (e.g. "ramesh@whyd.in")
        from        — sender email address
        from_name   — sender display name (optional)
        subject     — email subject
        message_id  — RFC 5322 Message-ID header
        text        — plain-text body
        html        — HTML body
        size        — raw message size in bytes (optional)
        has_attachments — boolean (optional)
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request: Request) -> Response:
        # --- HMAC signature verification ---
        secret = getattr(settings, "CLOUDFLARE_EMAIL_WEBHOOK_SECRET", "")
        if secret:
            sig = request.headers.get("X-Webhook-Signature", "")
            body = request.body
            expected = hmac.new(
                secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(sig, expected):
                return error_response("unauthorized", "Invalid webhook signature.", status=401)

        # --- Parse recipient → username + domain ---
        recipient = request.data.get("to", "")
        if "@" not in recipient:
            return error_response("bad_request", "Missing or invalid 'to' field.", status=400)

        username, domain = recipient.rsplit("@", 1)

        # --- Look up WhydudEmail by (username, domain) ---
        whydud_email = (
            WhydudEmail.objects
            .filter(username=username, domain=domain, is_active=True)
            .select_related("user")
            .first()
        )
        if not whydud_email:
            logger.warning("inbound_email_unknown_recipient", extra={"recipient": recipient})
            return error_response("not_found", "Unknown recipient.", status=404)

        # --- Encrypt body (AES-256-GCM) ---
        body_text_enc = encrypt(request.data.get("text", ""))
        body_html_enc = encrypt(request.data.get("html", ""))

        # --- Create InboxEmail record ---
        message_id = request.data.get("message_id", "") or str(uuid.uuid4())
        inbox_email = InboxEmail.objects.create(
            user_id=whydud_email.user_id,
            whydud_email=whydud_email,
            direction=InboxEmail.Direction.INBOUND,
            message_id=message_id,
            sender_address=request.data.get("from", ""),
            sender_name=request.data.get("from_name", ""),
            recipient_address=recipient,
            subject=request.data.get("subject", ""),
            body_text_encrypted=body_text_enc,
            body_html_encrypted=body_html_enc,
            raw_size_bytes=request.data.get("size"),
            has_attachments=bool(request.data.get("has_attachments", False)),
            received_at=timezone.now(),
        )

        # --- Update WhydudEmail stats ---
        WhydudEmail.objects.filter(pk=whydud_email.pk).update(
            total_emails_received=F("total_emails_received") + 1,
            last_email_received_at=timezone.now(),
        )

        # --- Dispatch Celery parsing task ---
        process_inbound_email.delay(str(inbox_email.id))

        return Response({"ok": True, "email_id": str(inbox_email.id)}, status=202)


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
