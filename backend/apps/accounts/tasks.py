"""Celery tasks for accounts app."""
from celery import shared_task
from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


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
