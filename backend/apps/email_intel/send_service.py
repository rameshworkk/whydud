"""Email sending service — sends from user's @whyd.* address via Resend API.

Architecture §6 "Email Pipeline — Sending":
  1. User owns active WhydudEmail
  2. Rate limit: ≤10 sends/day, ≤50/month (Redis counter)
  3. Recipient is allowed (replied-to sender OR known marketplace domain OR any for MVP)
  4. Sanitize HTML body with nh3
  5. Call Resend API
  6. Store sent email in inbox_emails (direction='outbound')
  7. Return resend message_id
"""
import logging
import time
import uuid
from dataclasses import dataclass

import nh3
import resend
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone

from apps.accounts.models import WhydudEmail
from common.app_settings import EmailSendConfig
from common.encryption import encrypt

from .models import InboxEmail

logger = logging.getLogger(__name__)


class SendEmailError(Exception):
    """Raised when email sending fails."""

    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


@dataclass
class SendResult:
    """Result of a successful send."""
    inbox_email_id: str
    resend_message_id: str


def _check_rate_limit(user_id: str) -> None:
    """Enforce daily and monthly send limits via Redis counters."""
    daily_key = f"email_send:daily:{user_id}"
    monthly_key = f"email_send:monthly:{user_id}"

    try:
        daily_count = cache.get(daily_key, 0)
        monthly_count = cache.get(monthly_key, 0)
    except Exception:
        # Redis unavailable — fail open
        return

    if daily_count >= EmailSendConfig.daily_send_limit():
        raise SendEmailError(
            "rate_limit_exceeded",
            f"Daily send limit reached ({EmailSendConfig.daily_send_limit()}/day).",
        )
    if monthly_count >= EmailSendConfig.monthly_send_limit():
        raise SendEmailError(
            "rate_limit_exceeded",
            f"Monthly send limit reached ({EmailSendConfig.monthly_send_limit()}/month).",
        )


def _increment_rate_counters(user_id: str) -> None:
    """Bump daily and monthly send counters after successful send."""
    daily_key = f"email_send:daily:{user_id}"
    monthly_key = f"email_send:monthly:{user_id}"

    try:
        # Daily: expires at end of current day (max 86400s)
        pipe = cache.client.get_client().pipeline()  # type: ignore[attr-defined]
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        pipe.incr(monthly_key)
        pipe.expire(monthly_key, 30 * 86400)
        pipe.execute()
    except Exception:
        # Redis unavailable — counters not incremented; fail open
        logger.warning("email_send_rate_counter_failed", extra={"user_id": user_id})


def _validate_recipient(user_id: str, to_address: str) -> None:
    """Validate recipient is allowed per Architecture §6.

    For MVP: any user-entered address is allowed.
    Post-MVP: restrict to replied-to senders + known marketplace domains.
    """
    # MVP: allow all recipients (Architecture §6 says "Any user-entered address
    # (no limits for MVP)")
    if not to_address or "@" not in to_address:
        raise SendEmailError("invalid_recipient", "Invalid recipient email address.")


def _sanitize_html(html: str) -> str:
    """Sanitize HTML body with nh3 (Architecture §6 step 4)."""
    if not html:
        return ""
    return nh3.clean(html)


def _strip_tags(html: str) -> str:
    """Strip all HTML tags for plain-text fallback."""
    if not html:
        return ""
    return nh3.clean(html, tags=set())


def send_email(
    from_user_id: str,
    to_address: str,
    subject: str,
    body_html: str,
    body_text: str | None = None,
    reply_to_message_id: str | None = None,
) -> SendResult:
    """Send an email via Resend API from user's @whyd.* address.

    Args:
        from_user_id: UUID of the sending user.
        to_address: Recipient email address.
        subject: Email subject line.
        body_html: HTML body content (will be sanitized with nh3).
        body_text: Optional plain-text body. If None, derived from body_html.
        reply_to_message_id: RFC 5322 Message-ID for In-Reply-To threading.

    Returns:
        SendResult with inbox_email_id and resend_message_id.

    Raises:
        SendEmailError: On validation failure, rate limit, or API error.
    """
    # 1. User owns active WhydudEmail
    try:
        whydud_email = WhydudEmail.objects.select_related("user").get(
            user_id=from_user_id, is_active=True
        )
    except WhydudEmail.DoesNotExist:
        raise SendEmailError(
            "no_whydud_email",
            "User does not have an active @whyd.* email address.",
        )

    # 2. Rate limit
    _check_rate_limit(str(from_user_id))

    # 3. Validate recipient
    _validate_recipient(str(from_user_id), to_address)

    # 4. Sanitize HTML
    sanitized_html = _sanitize_html(body_html)
    plain_text = body_text or _strip_tags(body_html)

    # 5. Call Resend API
    api_key = getattr(settings, "RESEND_API_KEY", "")
    if not api_key:
        raise SendEmailError("config_error", "RESEND_API_KEY is not configured.")

    resend.api_key = api_key
    from_address = f"{whydud_email.username}@{whydud_email.domain}"
    display_name = whydud_email.user.name or whydud_email.username

    send_params: dict = {
        "from": f"{display_name} <{from_address}>",
        "to": [to_address],
        "subject": subject,
        "html": sanitized_html,
        "text": plain_text,
        "reply_to": from_address,
    }

    # Threading headers for reply
    if reply_to_message_id:
        send_params["headers"] = {
            "In-Reply-To": reply_to_message_id,
            "References": reply_to_message_id,
        }

    try:
        response = resend.Emails.send(send_params)
    except Exception as exc:
        logger.error(
            "resend_api_error",
            extra={"user_id": str(from_user_id), "error": str(exc)},
        )
        raise SendEmailError("send_failed", f"Failed to send email: {exc}")

    resend_id = response.get("id", "") if isinstance(response, dict) else getattr(response, "id", "")

    # 6. Store outbound email in inbox_emails
    inbox_email = InboxEmail.objects.create(
        user_id=from_user_id,
        whydud_email=whydud_email,
        direction=InboxEmail.Direction.OUTBOUND,
        message_id=str(uuid.uuid4()),
        sender_address=from_address,
        sender_name=display_name,
        recipient_address=to_address,
        subject=subject,
        body_text_encrypted=encrypt(plain_text),
        body_html_encrypted=encrypt(sanitized_html),
        resend_message_id=resend_id,
        is_read=True,  # Outbound is always "read"
        parse_status=InboxEmail.ParseStatus.SKIPPED,
        received_at=timezone.now(),
    )

    # 7. Bump rate counters
    _increment_rate_counters(str(from_user_id))

    logger.info(
        "email_sent",
        extra={
            "user_id": str(from_user_id),
            "to": to_address,
            "resend_id": resend_id,
            "inbox_email_id": str(inbox_email.id),
        },
    )

    return SendResult(
        inbox_email_id=str(inbox_email.id),
        resend_message_id=resend_id,
    )
