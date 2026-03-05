"""Celery tasks for accounts app."""
import json
import logging
import os
import uuid

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

DELETION_GRACE_PERIOD_DAYS = 30

# Maps Notification.Type values to NotificationPreference field names.
# subscription_renewal has no user-facing preference — always delivered.
NOTIFICATION_TYPE_TO_PREF_FIELD: dict[str, str | None] = {
    "price_drop": "price_drops",
    "return_window": "return_windows",
    "refund_delay": "refund_delays",
    "back_in_stock": "back_in_stock",
    "review_upvote": "review_upvotes",
    "price_alert": "price_alerts",
    "discussion_reply": "discussion_replies",
    "level_up": "level_up",
    "points_earned": "points_earned",
    "subscription_renewal": None,  # always delivered
}


@shared_task(queue="email")
def send_verification_email(user_id: str) -> None:
    """Send email verification link to new user."""
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    uid = urlsafe_base64_encode(force_bytes(str(user.pk)))
    token = default_token_generator.make_token(user)
    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    link = f"{frontend_url}/verify-email?uid={uid}&token={token}"

    send_mail(
        subject="Verify your Whydud email",
        message=f"Hi {user.name or 'there'},\n\nPlease verify your email by clicking the link below:\n\n{link}\n\nIf you didn't create an account, you can ignore this email.\n\n— Whydud",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task(queue="email")
def send_verification_otp(user_id: str, otp: str) -> None:
    """Send a 6-digit OTP for email verification."""
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    send_mail(
        subject="Your Whydud verification code",
        message=(
            f"Hi {user.name or 'there'},\n\n"
            f"Your verification code is: {otp}\n\n"
            f"This code expires in 10 minutes.\n\n"
            f"If you didn't create an account, you can ignore this email.\n\n"
            f"— Whydud"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task(queue="email")
def send_password_reset_email(user_id: str, uid: str, token: str) -> None:
    """Send password reset link."""
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
    link = f"{frontend_url}/reset-password?uid={uid}&token={token}"

    send_mail(
        subject="Reset your Whydud password",
        message=f"Hi {user.name or 'there'},\n\nYou requested a password reset. Click the link below:\n\n{link}\n\nThis link expires in 24 hours. If you didn't request this, you can ignore this email.\n\n— Whydud",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@shared_task(queue="default")
def hard_delete_user(user_id: str) -> None:
    """Hard-delete all user data (DPDP compliance).

    Called 30 days after soft-delete request. Checks that the user hasn't
    cancelled the deletion (deletion_requested_at is still set).
    """
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.info("hard_delete_user: user %s already deleted", user_id)
        return

    # User may have cancelled — check deletion_requested_at is still set
    if user.deletion_requested_at is None:
        logger.info("hard_delete_user: user %s cancelled deletion, skipping", user_id)
        return

    user_email = user.email
    logger.info("hard_delete_user: starting hard delete for %s", user_email)

    # 1. Delete @whyd.* emails + parsed orders + inbox emails
    try:
        from apps.email_intel.models import (
            InboxEmail, ParsedOrder, RefundTracking, ReturnWindow,
            DetectedSubscription, EmailSource,
        )
        inbox_count = InboxEmail.objects.filter(user=user).count()
        InboxEmail.objects.filter(user=user).delete()
        ParsedOrder.objects.filter(user=user).delete()
        RefundTracking.objects.filter(user=user).delete()
        ReturnWindow.objects.filter(user=user).delete()
        DetectedSubscription.objects.filter(user=user).delete()
        EmailSource.objects.filter(user=user).delete()
        logger.info("hard_delete_user: deleted %d inbox emails for %s", inbox_count, user_email)
    except Exception as exc:
        logger.warning("hard_delete_user: email_intel cleanup error: %s", exc)

    # 2. Anonymize reviews (keep content, remove user association)
    try:
        from apps.reviews.models import Review, ReviewVote, ReviewerProfile
        reviews_count = Review.objects.filter(user=user).count()
        Review.objects.filter(user=user).update(
            user=None, reviewer_name="Deleted User"
        )
        ReviewVote.objects.filter(user=user).delete()
        ReviewerProfile.objects.filter(user=user).delete()
        logger.info("hard_delete_user: anonymized %d reviews for %s", reviews_count, user_email)
    except Exception as exc:
        logger.warning("hard_delete_user: reviews cleanup error: %s", exc)

    # 3. Delete wishlists + items
    try:
        from apps.wishlists.models import Wishlist
        Wishlist.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: wishlists cleanup error: %s", exc)

    # 4. Delete price alerts
    try:
        from apps.pricing.models import PriceAlert
        PriceAlert.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: price alerts cleanup error: %s", exc)

    # 5. Delete rewards data
    try:
        from apps.rewards.models import PointsLedger, RewardBalance, GiftCardRedemption
        PointsLedger.objects.filter(user=user).delete()
        GiftCardRedemption.objects.filter(user=user).delete()
        RewardBalance.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: rewards cleanup error: %s", exc)

    # 6. Delete discussions (threads, replies, votes)
    try:
        from apps.discussions.models import DiscussionThread, DiscussionReply, DiscussionVote
        DiscussionVote.objects.filter(user=user).delete()
        DiscussionReply.objects.filter(user=user).delete()
        DiscussionThread.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: discussions cleanup error: %s", exc)

    # 7. Delete TCO profile
    try:
        from apps.tco.models import UserTCOProfile
        UserTCOProfile.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: TCO cleanup error: %s", exc)

    # 8. Delete stock alerts, compare sessions, recently viewed
    try:
        from apps.products.models import StockAlert, CompareSession, RecentlyViewed
        StockAlert.objects.filter(user=user).delete()
        CompareSession.objects.filter(user=user).delete()
        RecentlyViewed.objects.filter(user=user).delete()
    except Exception as exc:
        logger.warning("hard_delete_user: products cleanup error: %s", exc)

    # 9. Delete notifications + preferences (CASCADE should handle, but be explicit)
    from .models import Notification, NotificationPreference
    Notification.objects.filter(user=user).delete()
    try:
        user.notification_preferences.delete()
    except NotificationPreference.DoesNotExist:
        pass

    # 10. Delete remaining account-level data (OAuth already deleted at soft-delete)
    from .models import PaymentMethod, WhydudEmail, PurchasePreference, MarketplacePreference
    PaymentMethod.objects.filter(user=user).delete()
    PurchasePreference.objects.filter(user=user).delete()
    try:
        user.marketplace_preferences.delete()
    except MarketplacePreference.DoesNotExist:
        pass
    try:
        user.whydud_email.delete()
    except WhydudEmail.DoesNotExist:
        pass

    # 11. Delete auth tokens
    from rest_framework.authtoken.models import Token
    Token.objects.filter(user=user).delete()

    # 12. Finally delete the User record
    user.delete()
    logger.info("hard_delete_user: completed hard delete for %s", user_email)


# Keep old name as alias for backwards compatibility with any queued tasks
delete_user_data = hard_delete_user


@shared_task(queue="email")
def send_deletion_confirmation_email(user_id: str) -> None:
    """Send email confirming account deletion has been requested."""
    from .models import User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        return

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    send_mail(
        subject="Your Whydud account deletion request",
        message=(
            f"Hi {user.name or 'there'},\n\n"
            f"We've received your request to delete your Whydud account.\n\n"
            f"Your account will be permanently deleted in {DELETION_GRACE_PERIOD_DAYS} days.\n\n"
            f"If you change your mind, simply log in to your account and "
            f"visit {frontend_url}/settings to cancel the deletion.\n\n"
            f"— Whydud"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=True,
    )


@shared_task(queue="default")
def generate_data_export(user_id: str) -> str:
    """Generate a JSON data export for DPDP right to portability.

    Returns the download URL path. The file is stored in MEDIA_ROOT/exports/
    and expires after 24 hours (cleaned up by a separate periodic task or on access).
    """
    from .models import User
    from .serializers import UserSerializer

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        raise ValueError(f"User {user_id} not found")

    export_data: dict = {
        "exported_at": timezone.now().isoformat(),
        "user_id": str(user.pk),
    }

    # --- Profile ---
    export_data["profile"] = UserSerializer(user).data
    export_data["profile"]["created_at"] = user.created_at.isoformat()

    # --- @whyd.xyz email ---
    try:
        whydud_email = user.whydud_email
        export_data["whydud_email"] = {
            "username": whydud_email.username,
            "domain": whydud_email.domain,
            "email_address": whydud_email.email_address,
            "is_active": whydud_email.is_active,
            "total_emails_received": whydud_email.total_emails_received,
            "total_orders_detected": whydud_email.total_orders_detected,
            "created_at": whydud_email.created_at.isoformat(),
        }
    except Exception:
        export_data["whydud_email"] = None

    # --- Reviews ---
    try:
        from apps.reviews.models import Review
        reviews = Review.objects.filter(user=user).select_related("product")
        export_data["reviews"] = [
            {
                "product": str(r.product.title) if r.product else None,
                "rating": r.rating,
                "title": r.title,
                "body": r.body,
                "created_at": r.created_at.isoformat() if hasattr(r, "created_at") else None,
            }
            for r in reviews
        ]
    except Exception:
        export_data["reviews"] = []

    # --- Wishlists ---
    try:
        from apps.wishlists.models import Wishlist
        wishlists = Wishlist.objects.filter(user=user).prefetch_related("items")
        export_data["wishlists"] = [
            {
                "name": w.name,
                "is_default": w.is_default,
                "items": [
                    {
                        "product_id": str(item.product_id),
                        "price_when_added": str(item.price_when_added) if item.price_when_added else None,
                        "target_price": str(item.target_price) if item.target_price else None,
                        "notes": item.notes,
                        "added_at": item.added_at.isoformat() if hasattr(item, "added_at") else None,
                    }
                    for item in w.items.all()
                ],
                "created_at": w.created_at.isoformat(),
            }
            for w in wishlists
        ]
    except Exception:
        export_data["wishlists"] = []

    # --- Parsed orders (purchases) ---
    try:
        from apps.email_intel.models import ParsedOrder
        orders = ParsedOrder.objects.filter(user=user)
        export_data["purchases"] = [
            {
                "order_id": o.order_id,
                "marketplace": o.marketplace,
                "product_name": o.product_name,
                "quantity": o.quantity,
                "price_paid": str(o.price_paid) if o.price_paid else None,
                "total_amount": str(o.total_amount) if o.total_amount else None,
                "order_date": o.order_date.isoformat() if o.order_date else None,
                "seller_name": o.seller_name,
                "created_at": o.created_at.isoformat(),
            }
            for o in orders
        ]
    except Exception:
        export_data["purchases"] = []

    # --- Preferences ---
    try:
        from .models import NotificationPreference
        prefs = user.notification_preferences
        export_data["notification_preferences"] = {
            "price_drops": prefs.price_drops,
            "return_windows": prefs.return_windows,
            "back_in_stock": prefs.back_in_stock,
            "review_upvotes": prefs.review_upvotes,
            "price_alerts": prefs.price_alerts,
            "discussion_replies": prefs.discussion_replies,
        }
    except Exception:
        export_data["notification_preferences"] = None

    # --- Rewards ---
    try:
        from apps.rewards.models import PointsLedger, RewardBalance
        balance = RewardBalance.objects.filter(user=user).first()
        if balance:
            export_data["rewards"] = {
                "current_balance": balance.current_balance,
                "total_earned": balance.total_earned,
                "total_spent": balance.total_spent,
            }
        ledger = PointsLedger.objects.filter(user=user).order_by("-created_at")
        export_data["rewards_history"] = [
            {
                "action": entry.action,
                "points": entry.points,
                "description": entry.description,
                "created_at": entry.created_at.isoformat(),
            }
            for entry in ledger
        ]
    except Exception:
        export_data["rewards"] = None
        export_data["rewards_history"] = []

    # --- Notifications (last 100) ---
    try:
        from .models import Notification
        notifs = Notification.objects.filter(user=user).order_by("-created_at")[:100]
        export_data["notifications"] = [
            {
                "type": n.type,
                "title": n.title,
                "body": n.body,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat(),
            }
            for n in notifs
        ]
    except Exception:
        export_data["notifications"] = []

    # --- Write to file ---
    export_dir = os.path.join(settings.MEDIA_ROOT, "exports")
    os.makedirs(export_dir, exist_ok=True)

    filename = f"whydud-export-{user_id}-{uuid.uuid4().hex[:8]}.json"
    filepath = os.path.join(export_dir, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False, default=str)

    logger.info("generate_data_export: wrote %s for user %s", filename, user_id)

    # Return the download URL path
    return f"{settings.MEDIA_URL}exports/{filename}"


@shared_task(queue="email")
def sync_gmail_account(user_id: str) -> None:
    """Background Gmail OAuth sync — runs every 6 hours per connected user."""
    # TODO Sprint 2 (P1 feature)
    pass


@shared_task(queue="default")
def create_notification(
    user_id: str,
    type: str,
    title: str,
    body: str | None = None,
    action_url: str | None = None,
    action_label: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict | None = None,
) -> int | None:
    """Create an in-app notification and optionally queue an email.

    Checks NotificationPreference to decide whether to create the in-app
    notification and whether to send an email.  Returns the notification id
    on success, or None if the notification was suppressed by preferences.
    """
    from .models import Notification, NotificationPreference, User

    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("create_notification: user %s not found", user_id)
        return None

    # --- Check user preferences -------------------------------------------
    pref_field = NOTIFICATION_TYPE_TO_PREF_FIELD.get(type)
    try:
        prefs = user.notification_preferences
    except NotificationPreference.DoesNotExist:
        # No preference row → use model defaults (in_app=True for all)
        prefs = None

    if pref_field and prefs:
        channel_pref = getattr(prefs, pref_field, None)
        if isinstance(channel_pref, dict) and not channel_pref.get("in_app", True):
            # User explicitly disabled in-app for this type
            logger.info(
                "create_notification: suppressed %s for user %s (in_app=False)",
                type,
                user_id,
            )
            return None

    # --- Create Notification record ----------------------------------------
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        body=body or "",
        action_url=action_url or "",
        action_label=action_label or "",
        entity_type=entity_type or "",
        entity_id=entity_id or "",
        metadata=metadata or {},
    )

    # --- Determine if email should be sent ---------------------------------
    should_email = False
    if pref_field is None:
        # Types without a preference (e.g. subscription_renewal) always email
        should_email = True
    elif prefs:
        channel_pref = getattr(prefs, pref_field, None)
        if isinstance(channel_pref, dict):
            should_email = channel_pref.get("email", False)
    else:
        # No preference row → fall back to model field defaults.
        # Reconstruct the default to check the email channel.
        from .models import _pref_in_app_and_email, _pref_in_app_only

        defaults = {
            "price_drops": _pref_in_app_and_email,
            "return_windows": _pref_in_app_and_email,
            "refund_delays": _pref_in_app_and_email,
            "back_in_stock": _pref_in_app_only,
            "review_upvotes": _pref_in_app_only,
            "price_alerts": _pref_in_app_and_email,
            "discussion_replies": _pref_in_app_only,
            "level_up": _pref_in_app_only,
            "points_earned": _pref_in_app_only,
        }
        default_fn = defaults.get(pref_field)
        if default_fn:
            should_email = default_fn().get("email", False)

    if should_email:
        send_notification_email.delay(notification.pk)

    return notification.pk


@shared_task(queue="email", max_retries=3, default_retry_delay=60)
def send_notification_email(notification_id: int) -> bool:
    """Send an email for an existing notification via Resend (SMTP).

    Renders a plain-text and HTML email, sends it to the user's preferred
    email (whydud address or personal), and marks ``email_sent`` on the
    notification record.  Returns True on success.
    """
    from .models import Notification

    try:
        notification = Notification.objects.select_related("user").get(pk=notification_id)
    except Notification.DoesNotExist:
        logger.warning("send_notification_email: notification %s not found", notification_id)
        return False

    user = notification.user

    # Determine recipient — prefer @whyd.* address, fall back to personal email
    recipient = user.email
    try:
        whydud_email = user.whydud_email
        if whydud_email and whydud_email.is_active:
            recipient = whydud_email.email_address
    except Exception:
        pass  # No whydud email — use personal email

    frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")

    # --- Build plain-text body ---------------------------------------------
    text_lines = [
        f"Hi {user.name or 'there'},",
        "",
        notification.title,
    ]
    if notification.body:
        text_lines += ["", notification.body]
    if notification.action_url:
        url = notification.action_url
        if url.startswith("/"):
            url = f"{frontend_url}{url}"
        label = notification.action_label or "View details"
        text_lines += ["", f"{label}: {url}"]
    text_lines += ["", "— Whydud"]
    plain_text = "\n".join(text_lines)

    # --- Build HTML body ---------------------------------------------------
    action_html = ""
    if notification.action_url:
        url = notification.action_url
        if url.startswith("/"):
            url = f"{frontend_url}{url}"
        label = notification.action_label or "View details"
        action_html = (
            f'<p style="margin:24px 0">'
            f'<a href="{url}" style="background:#F97316;color:#fff;'
            f'padding:10px 24px;border-radius:6px;text-decoration:none;'
            f'font-weight:600;display:inline-block">{label}</a></p>'
        )

    html_body = (
        f'<div style="font-family:Inter,system-ui,sans-serif;max-width:560px;'
        f'margin:0 auto;padding:32px 24px;color:#1E293B">'
        f'<p style="margin:0 0 8px;font-size:14px;color:#64748B">Whydud</p>'
        f'<h2 style="margin:0 0 16px;font-size:20px;font-weight:600">'
        f'{notification.title}</h2>'
        f'{"<p style=\"margin:0 0 16px;font-size:15px;line-height:1.6\">" + notification.body + "</p>" if notification.body else ""}'
        f'{action_html}'
        f'<hr style="border:none;border-top:1px solid #E2E8F0;margin:32px 0 16px">'
        f'<p style="font-size:12px;color:#94A3B8;margin:0">'
        f'You received this because of your notification preferences. '
        f'<a href="{frontend_url}/settings" style="color:#64748B">Manage preferences</a>'
        f'</p></div>'
    )

    # --- Send email --------------------------------------------------------
    try:
        send_mail(
            subject=notification.title,
            message=plain_text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[recipient],
            html_message=html_body,
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(
            "send_notification_email: failed for notification %s: %s",
            notification_id,
            exc,
        )
        raise send_notification_email.retry(exc=exc)

    # --- Mark as sent ------------------------------------------------------
    notification.email_sent = True
    notification.email_sent_at = timezone.now()
    notification.save(update_fields=["email_sent", "email_sent_at"])

    logger.info(
        "send_notification_email: sent %s (%s) to %s",
        notification_id,
        notification.type,
        recipient,
    )
    return True
