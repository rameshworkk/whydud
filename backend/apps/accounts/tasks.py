"""Celery tasks for accounts app."""
import logging

from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils import timezone
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

logger = logging.getLogger(__name__)

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
def delete_user_data(user_id: str) -> None:
    """Hard-delete all user data (DPDP compliance). Called 30 days after soft-delete."""
    # TODO Sprint 4
    pass


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
