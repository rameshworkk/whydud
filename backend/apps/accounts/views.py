"""Account views — auth, profile, card vault, @whyd.xyz email."""
import secrets

from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.cache import cache
from django.http import HttpResponseRedirect
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views import View
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.throttling import AuthRateThrottle
from common.utils import error_response, success_response

from .models import (
    MarketplacePreference, PaymentMethod, ReservedUsername, User, WhydudEmail,
    validate_whydud_username_format,
)
from .serializers import (
    ChangePasswordSerializer,
    DeleteAccountSerializer,
    ForgotPasswordSerializer,
    LoginSerializer,
    MarketplacePreferenceSerializer,
    PaymentMethodSerializer,
    RegisterSerializer,
    ResetPasswordSerializer,
    UserSerializer,
    WhydudEmailSerializer,
)

OTP_LENGTH = 6
OTP_TTL = 600  # 10 minutes
OTP_MAX_ATTEMPTS = 5


def _generate_otp() -> str:
    """Generate a cryptographically random 6-digit OTP."""
    return "".join(str(secrets.randbelow(10)) for _ in range(OTP_LENGTH))


class RegisterView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        name = serializer.validated_data.get("name", "")

        if User.objects.filter(email=email).exists():
            return error_response("email_taken", "An account with this email already exists.")

        # Look up referrer before creating user
        referral_code = serializer.validated_data.get("referral_code", "").strip().upper()
        referrer = None
        if referral_code:
            referrer = User.objects.filter(referral_code=referral_code).first()

        user = User.objects.create_user(
            email=email, password=password, name=name,
            referred_by=referrer,
        )
        token, _ = Token.objects.get_or_create(user=user)

        # Award referral points to the referrer
        if referrer:
            from apps.rewards.tasks import award_points_task
            award_points_task.delay(str(referrer.pk), 'referral_signup', str(user.pk))

        # Generate and send OTP for email verification
        otp = _generate_otp()
        cache.set(f"email_otp:{user.pk}", otp, OTP_TTL)
        cache.set(f"email_otp_attempts:{user.pk}", 0, OTP_TTL)
        from .tasks import send_verification_otp
        send_verification_otp.delay(str(user.pk), otp)

        return success_response(
            {"user": UserSerializer(user).data, "token": token.key},
            status=201,
        )


class LoginView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    LOCKOUT_THRESHOLD = 5
    LOCKOUT_DURATION = 900  # 15 minutes in seconds

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        email = serializer.validated_data["email"]
        lockout_key = f"login_lockout:{email}"

        # Check lockout before attempting authentication
        attempts = cache.get(lockout_key)
        if attempts is not None and attempts >= self.LOCKOUT_THRESHOLD:
            return error_response(
                "too_many_attempts",
                "Too many login attempts. Try again in 15 minutes.",
                status=429,
            )

        user = authenticate(
            request,
            username=email,
            password=serializer.validated_data["password"],
        )
        if not user:
            # Increment failed attempt counter
            new_count = cache.get(lockout_key)
            if new_count is None:
                cache.set(lockout_key, 1, self.LOCKOUT_DURATION)
            else:
                cache.incr(lockout_key)
                # Reset TTL on each failed attempt
                cache.touch(lockout_key, self.LOCKOUT_DURATION)
            return error_response("invalid_credentials", "Invalid email or password.", status=401)

        if not user.is_active:
            return error_response("account_suspended", "Your account has been suspended.", status=403)

        # Allow login for users with pending deletion (so they can restore),
        # but block truly suspended users (no deletion request).
        if user.is_suspended and user.deletion_requested_at is None:
            return error_response("account_suspended", "Your account has been suspended.", status=403)

        # Clear lockout on successful login
        cache.delete(lockout_key)

        user.last_login_at = timezone.now()
        user.save(update_fields=["last_login_at"])

        token, _ = Token.objects.get_or_create(user=user)
        return success_response({"user": UserSerializer(user).data, "token": token.key})


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        try:
            request.user.auth_token.delete()
        except Exception:
            pass
        return success_response({"detail": "Logged out."})


class ChangePasswordView(APIView):
    """Change password for authenticated user. Requires current password."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        if not request.user.check_password(serializer.validated_data["current_password"]):
            return error_response("wrong_password", "Current password is incorrect.", status=400)

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])

        # Re-create token so user stays logged in
        Token.objects.filter(user=request.user).delete()
        new_token, _ = Token.objects.get_or_create(user=request.user)

        return success_response({"detail": "Password updated.", "token": new_token.key})


class ForgotPasswordView(APIView):
    """Send password reset email with a one-time link."""
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = [AuthRateThrottle]

    def post(self, request: Request) -> Response:
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        email = serializer.validated_data["email"]
        # Always return success to prevent email enumeration
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return success_response({"detail": "If that email exists, a reset link has been sent."})

        uid = urlsafe_base64_encode(force_bytes(str(user.pk)))
        token = default_token_generator.make_token(user)

        from .tasks import send_password_reset_email
        send_password_reset_email.delay(str(user.pk), uid, token)

        return success_response({"detail": "If that email exists, a reset link has been sent."})


class ResetPasswordView(APIView):
    """Reset password using uid + token from email link."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        uid = serializer.validated_data["uid"]
        token = serializer.validated_data["token"]
        new_password = serializer.validated_data["new_password"]

        try:
            user_pk = force_str(urlsafe_base64_decode(uid))
            user = User.objects.get(pk=user_pk)
        except (ValueError, TypeError, User.DoesNotExist):
            return error_response("invalid_link", "This reset link is invalid or expired.", status=400)

        if not default_token_generator.check_token(user, token):
            return error_response("invalid_link", "This reset link is invalid or expired.", status=400)

        user.set_password(new_password)
        user.save(update_fields=["password"])

        # Invalidate all existing tokens — user must re-login
        Token.objects.filter(user=user).delete()

        return success_response({"detail": "Password has been reset. Please sign in."})


class VerifyEmailView(APIView):
    """Verify email address using a 6-digit OTP sent to the user's email."""
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        email = request.data.get("email", "").strip().lower()
        otp = request.data.get("otp", "").strip()

        if not email or not otp:
            return error_response("validation_error", "email and otp are required.")

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return error_response("invalid_otp", "Invalid OTP.", status=400)

        if user.email_verified:
            return success_response({"detail": "Email already verified."})

        attempts_key = f"email_otp_attempts:{user.pk}"
        attempts = cache.get(attempts_key, 0)
        if attempts >= OTP_MAX_ATTEMPTS:
            return error_response(
                "too_many_attempts",
                "Too many failed attempts. Request a new OTP.",
                status=429,
            )

        stored_otp = cache.get(f"email_otp:{user.pk}")
        if stored_otp is None:
            return error_response("otp_expired", "OTP has expired. Request a new one.", status=400)

        if str(stored_otp) != str(otp):
            cache.set(attempts_key, attempts + 1, OTP_TTL)
            return error_response("invalid_otp", "Invalid OTP.", status=400)

        # OTP matches — verify email
        user.email_verified = True
        user.save(update_fields=["email_verified"])
        cache.delete(f"email_otp:{user.pk}")
        cache.delete(attempts_key)

        return success_response({"detail": "Email verified successfully."})


class ResendVerificationEmailView(APIView):
    """Resend OTP verification email to the authenticated user."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        if request.user.email_verified:
            return success_response({"detail": "Email already verified."})

        otp = _generate_otp()
        cache.set(f"email_otp:{request.user.pk}", otp, OTP_TTL)
        cache.set(f"email_otp_attempts:{request.user.pk}", 0, OTP_TTL)
        from .tasks import send_verification_otp
        send_verification_otp.delay(str(request.user.pk), otp)

        return success_response({"detail": "Verification OTP sent."})


class OAuthCompleteView(View):
    """After AllAuth OAuth login, create a one-time code and redirect to frontend.

    AllAuth redirects here after successful Google OAuth. We create a short-lived
    code stored in Redis, then redirect the browser to the frontend callback page
    with `?code=XXX`. The frontend exchanges that code for a DRF token via
    OAuthExchangeCodeView. This avoids session cookie cross-port issues.
    """

    def get(self, request):
        frontend_url = settings.FRONTEND_URL

        if not request.user.is_authenticated:
            return HttpResponseRedirect(f"{frontend_url}/login?error=oauth_failed")

        token, _ = Token.objects.get_or_create(user=request.user)

        # One-time code: stored in Redis cache, expires in 60 seconds
        code = secrets.token_urlsafe(32)
        cache.set(f"oauth_code:{code}", {
            "token": token.key,
            "user_id": str(request.user.pk),
        }, timeout=60)

        return HttpResponseRedirect(f"{frontend_url}/auth/callback?code={code}")


class OAuthExchangeCodeView(APIView):
    """Exchange a one-time OAuth code for a DRF token.

    The frontend callback page sends the code it received from OAuthCompleteView.
    We look it up in Redis, return the token + user, and delete the code.
    """
    # Explicitly exclude SessionAuthentication to avoid CSRF enforcement.
    # The browser may carry a Django session cookie from the OAuth callback
    # (cookies are shared across ports on localhost), and SessionAuthentication
    # would reject the POST without a CSRF token.
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        code = request.data.get("code", "")
        if not code:
            return error_response("validation_error", "code is required.", status=400)

        data = cache.get(f"oauth_code:{code}")
        if not data:
            return error_response("invalid_code", "Code is invalid or expired.", status=400)

        # Delete immediately so the code can't be reused
        cache.delete(f"oauth_code:{code}")

        try:
            user = User.objects.get(pk=data["user_id"])
        except User.DoesNotExist:
            return error_response("user_not_found", "User not found.", status=400)

        return success_response({
            "user": UserSerializer(user).data,
            "token": data["token"],
        })


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return success_response(UserSerializer(request.user).data)

    def delete(self, request: Request) -> Response:
        # Redirect to dedicated DeleteAccountView endpoint
        return error_response(
            "use_dedicated_endpoint",
            "Use DELETE /api/v1/me/account with password confirmation.",
            status=400,
        )


class WhydudEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        try:
            email = request.user.whydud_email
            return success_response(WhydudEmailSerializer(email).data)
        except WhydudEmail.DoesNotExist:
            return error_response("not_found", "No @whyd.xyz email found.", status=404)

    def post(self, request: Request) -> Response:
        if hasattr(request.user, "whydud_email"):
            try:
                _ = request.user.whydud_email
                return error_response("already_exists", "You already have a @whyd.xyz email.")
            except WhydudEmail.DoesNotExist:
                pass

        serializer = WhydudEmailSerializer(data=request.data)
        if not serializer.is_valid():
            # Extract the first error message for a clean response
            first_error = next(iter(serializer.errors.values()))[0]
            return error_response("validation_error", str(first_error))

        email = serializer.save(user=request.user)
        request.user.has_whydud_email = True
        request.user.save(update_fields=["has_whydud_email"])

        from apps.rewards.tasks import award_points_task
        award_points_task.delay(str(request.user.pk), 'connect_email', str(email.pk))

        return success_response(WhydudEmailSerializer(email).data, status=201)


class WhydudEmailAvailabilityView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        username = request.query_params.get("username", "").lower().strip()
        if not username:
            return error_response("validation_error", "?username= is required.")

        if validate_whydud_username_format(username):
            return success_response({"available": False, "reason": "invalid_format"})

        if ReservedUsername.objects.filter(username=username).exists():
            return success_response({"available": False, "reason": "reserved"})

        available = not WhydudEmail.objects.filter(username=username).exists()
        return success_response({"available": available})


class PaymentMethodListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        methods = PaymentMethod.objects.filter(user=request.user).order_by(
            "-is_preferred", "-created_at"
        )
        return success_response(PaymentMethodSerializer(methods, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = PaymentMethodSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        method = serializer.save(user=request.user)
        return success_response(PaymentMethodSerializer(method).data, status=201)


class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: str) -> Response:
        method = PaymentMethod.objects.filter(user=request.user, pk=pk).first()
        if not method:
            return error_response("not_found", "Payment method not found.", status=404)
        serializer = PaymentMethodSerializer(method, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, pk: str) -> Response:
        method = PaymentMethod.objects.filter(user=request.user, pk=pk).first()
        if not method:
            return error_response("not_found", "Payment method not found.", status=404)
        method.delete()
        return success_response({"detail": "Deleted."})


class MarketplacePreferenceView(APIView):
    """GET + PUT /api/v1/me/marketplace-preferences

    GET  — returns preferred marketplace IDs + full marketplace list.
    PUT  — updates preferred marketplace IDs (empty list = show all).
    """

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        pref, _ = MarketplacePreference.objects.get_or_create(user=request.user)
        return success_response(MarketplacePreferenceSerializer(pref).data)

    def put(self, request: Request) -> Response:
        pref, _ = MarketplacePreference.objects.get_or_create(user=request.user)
        serializer = MarketplacePreferenceSerializer(pref, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)


# ---------------------------------------------------------------------------
# DPDP Compliance: Account deletion, restoration, and data export
# ---------------------------------------------------------------------------

DELETION_GRACE_PERIOD_DAYS = 30


class DeleteAccountView(APIView):
    """DELETE /api/v1/me/account — soft-delete with 30-day grace period."""

    permission_classes = [IsAuthenticated]

    def delete(self, request: Request) -> Response:
        serializer = DeleteAccountSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        if not request.user.check_password(serializer.validated_data["password"]):
            return error_response("wrong_password", "Password is incorrect.", status=400)

        if request.user.deletion_requested_at is not None:
            return error_response(
                "already_requested",
                "Account deletion already requested.",
            )

        user = request.user
        now = timezone.now()

        # Soft-delete: mark as suspended + record deletion request time
        user.is_suspended = True
        user.deletion_requested_at = now
        user.save(update_fields=["is_suspended", "deletion_requested_at"])

        # Immediately revoke OAuth tokens (don't wait 30 days)
        from .models import OAuthConnection
        OAuthConnection.objects.filter(user=user).delete()

        # Invalidate auth token
        Token.objects.filter(user=user).delete()

        # Schedule hard delete after grace period
        from .tasks import hard_delete_user
        hard_delete_user.apply_async(
            args=[str(user.pk)],
            countdown=DELETION_GRACE_PERIOD_DAYS * 86400,
        )

        # Send confirmation email
        from .tasks import send_deletion_confirmation_email
        send_deletion_confirmation_email.delay(str(user.pk))

        return success_response({
            "detail": (
                f"Your account will be permanently deleted in "
                f"{DELETION_GRACE_PERIOD_DAYS} days. "
                f"You can restore it before then by logging in."
            ),
            "deletion_requested_at": now.isoformat(),
            "permanent_deletion_at": (
                now + timezone.timedelta(days=DELETION_GRACE_PERIOD_DAYS)
            ).isoformat(),
        })


class RestoreAccountView(APIView):
    """POST /api/v1/me/account/restore — cancel pending deletion."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        user = request.user

        if user.deletion_requested_at is None:
            return error_response(
                "no_deletion_pending",
                "No account deletion is pending.",
            )

        # Restore account
        user.is_suspended = False
        user.deletion_requested_at = None
        user.save(update_fields=["is_suspended", "deletion_requested_at"])

        return success_response({
            "detail": "Account deletion cancelled. Your account has been restored.",
        })


class ExportDataView(APIView):
    """GET /api/v1/me/export — queue data export and return task ID."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        # Rate limit: one export per hour
        export_key = f"data_export:{request.user.pk}"
        if cache.get(export_key):
            return error_response(
                "export_in_progress",
                "A data export is already in progress. Please wait.",
                status=429,
            )

        from .tasks import generate_data_export
        task = generate_data_export.delay(str(request.user.pk))

        # Mark export as in-progress for 1 hour
        cache.set(export_key, task.id, 3600)

        return success_response(
            {"task_id": task.id, "detail": "Data export started. This may take a few minutes."},
            status=202,
        )


class ExportStatusView(APIView):
    """GET /api/v1/me/export/<task_id> — check export status."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, task_id: str) -> Response:
        from celery.result import AsyncResult

        result = AsyncResult(task_id)

        if result.state == "PENDING":
            return success_response({"status": "pending"})
        elif result.state == "SUCCESS":
            download_url = result.result
            return success_response({
                "status": "completed",
                "download_url": download_url,
            })
        elif result.state == "FAILURE":
            return error_response(
                "export_failed",
                "Data export failed. Please try again.",
                status=500,
            )
        else:
            return success_response({"status": result.state.lower()})
