"""Razorpay subscription views — create order, verify payment, cancel, status."""
import logging

import razorpay
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import SubscriptionConfig
from common.utils import error_response, success_response

logger = logging.getLogger(__name__)


def _get_razorpay_client() -> razorpay.Client:
    return razorpay.Client(
        auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
    )


class SubscriptionCreateView(APIView):
    """Create a Razorpay order for the Pro subscription (₹99/month)."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = request.user

        if user.subscription_tier == "premium":
            if user.subscription_expires_at and user.subscription_expires_at > timezone.now():
                return error_response(
                    "already_subscribed",
                    "You already have an active Pro subscription.",
                )

        amount_paisa = SubscriptionConfig.pro_amount_paisa()
        client = _get_razorpay_client()

        try:
            order = client.order.create({
                "amount": amount_paisa,
                "currency": "INR",
                "receipt": f"sub_{user.pk}",
                "notes": {
                    "user_id": str(user.pk),
                    "plan": "pro",
                },
            })
        except Exception:
            logger.exception("Razorpay order creation failed for user %s", user.pk)
            return error_response(
                "payment_error",
                "Could not create payment order. Please try again.",
                status=502,
            )

        # Store order ID in cache so verify can validate it belongs to this user
        cache.set(
            f"subscription_order:{order['id']}",
            str(user.pk),
            timeout=SubscriptionConfig.order_cache_ttl(),
        )

        return success_response({
            "order_id": order["id"],
            "amount": amount_paisa,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
        }, status=201)


class SubscriptionVerifyView(APIView):
    """Verify Razorpay payment signature and activate Pro subscription."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        razorpay_order_id = request.data.get("razorpay_order_id", "")
        razorpay_payment_id = request.data.get("razorpay_payment_id", "")
        razorpay_signature = request.data.get("razorpay_signature", "")

        if not all([razorpay_order_id, razorpay_payment_id, razorpay_signature]):
            return error_response(
                "validation_error",
                "razorpay_order_id, razorpay_payment_id, and razorpay_signature are required.",
            )

        # Verify this order belongs to the requesting user
        cached_user_id = cache.get(f"subscription_order:{razorpay_order_id}")
        if cached_user_id != str(request.user.pk):
            return error_response(
                "invalid_order",
                "This order does not belong to your account.",
                status=403,
            )

        # Verify Razorpay signature
        client = _get_razorpay_client()
        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature,
            })
        except razorpay.errors.SignatureVerificationError:
            return error_response(
                "signature_invalid",
                "Payment verification failed. Please contact support.",
                status=400,
            )

        # Activate subscription
        user = request.user
        user.subscription_tier = "premium"
        user.subscription_expires_at = timezone.now() + timezone.timedelta(
            days=SubscriptionConfig.pro_duration_days()
        )
        user.save(update_fields=["subscription_tier", "subscription_expires_at"])

        # Clean up cache
        cache.delete(f"subscription_order:{razorpay_order_id}")

        # Queue renewal notification
        from .tasks import create_notification

        create_notification.delay(
            user_id=str(user.pk),
            type="subscription_renewal",
            title="Pro subscription activated",
            body="Your Whydud Pro subscription is now active. Enjoy unlimited alerts, ad-free browsing, and priority support.",
        )

        return success_response({
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": user.subscription_expires_at.isoformat(),
        })


class SubscriptionCancelView(APIView):
    """Cancel the user's Pro subscription (reverts to Free at expiry)."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = request.user

        if user.subscription_tier != "premium":
            return error_response(
                "not_subscribed",
                "You do not have an active Pro subscription.",
            )

        # Downgrade immediately
        user.subscription_tier = "free"
        user.subscription_expires_at = None
        user.save(update_fields=["subscription_tier", "subscription_expires_at"])

        from .tasks import create_notification

        create_notification.delay(
            user_id=str(user.pk),
            type="subscription_renewal",
            title="Pro subscription cancelled",
            body="Your Pro subscription has been cancelled. You can re-subscribe anytime.",
        )

        return success_response({"detail": "Subscription cancelled."})


class SubscriptionStatusView(APIView):
    """Return the current subscription status for the authenticated user."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        user = request.user
        is_active = (
            user.subscription_tier == "premium"
            and user.subscription_expires_at is not None
            and user.subscription_expires_at > timezone.now()
        )

        return success_response({
            "subscription_tier": user.subscription_tier,
            "subscription_expires_at": (
                user.subscription_expires_at.isoformat()
                if user.subscription_expires_at
                else None
            ),
            "is_active": is_active,
            "plan": {
                "name": "Pro" if is_active else "Free",
                "amount": SubscriptionConfig.pro_amount_paisa() if is_active else 0,
                "currency": "INR",
                "interval": "monthly",
            },
        })
