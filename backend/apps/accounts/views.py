"""Account views — auth, profile, card vault, @whyd.xyz email."""
import re

from django.contrib.auth import authenticate
from django.utils import timezone
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from .models import PaymentMethod, ReservedUsername, User, WhydudEmail
from .serializers import (
    LoginSerializer,
    PaymentMethodSerializer,
    RegisterSerializer,
    UserSerializer,
    WhydudEmailSerializer,
)

# Valid username: 3–30 chars, alphanumeric + dots/hyphens/underscores, must start/end with alnum
_USERNAME_RE = re.compile(r'^[a-z0-9][a-z0-9._-]{1,28}[a-z0-9]$')


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        email = serializer.validated_data["email"]
        password = serializer.validated_data["password"]
        name = serializer.validated_data.get("name", "")

        if User.objects.filter(email=email).exists():
            return error_response("email_taken", "An account with this email already exists.")

        user = User.objects.create_user(email=email, password=password, name=name)
        token, _ = Token.objects.get_or_create(user=user)
        return success_response(
            {"user": UserSerializer(user).data, "token": token.key},
            status=201,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        user = authenticate(
            request,
            username=serializer.validated_data["email"],
            password=serializer.validated_data["password"],
        )
        if not user:
            return error_response("invalid_credentials", "Invalid email or password.", status=401)

        if not user.is_active or getattr(user, "is_suspended", False):
            return error_response("account_suspended", "Your account has been suspended.", status=403)

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


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        return success_response(UserSerializer(request.user).data)

    def delete(self, request: Request) -> Response:
        # TODO Sprint 4: DPDP-compliant account deletion
        return error_response("not_implemented", "Account deletion available in Sprint 4.", status=501)


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

        username = request.data.get("username", "").lower().strip()
        if not username:
            return error_response("validation_error", "username is required.")

        if not _USERNAME_RE.match(username):
            return error_response(
                "invalid_username",
                "Username must be 3–30 characters, start and end with a letter or digit, "
                "and contain only letters, digits, dots, hyphens, or underscores.",
            )

        if ReservedUsername.objects.filter(username=username).exists():
            return error_response("username_reserved", "This username is reserved.")

        if WhydudEmail.objects.filter(username=username).exists():
            return error_response("username_taken", "This username is already taken.")

        email = WhydudEmail.objects.create(user=request.user, username=username)
        request.user.has_whydud_email = True
        request.user.save(update_fields=["has_whydud_email"])
        return success_response(WhydudEmailSerializer(email).data, status=201)


class WhydudEmailAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        username = request.query_params.get("username", "").lower().strip()
        if not username:
            return error_response("validation_error", "?username= is required.")

        if not _USERNAME_RE.match(username):
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
