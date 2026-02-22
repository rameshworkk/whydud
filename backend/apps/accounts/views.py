"""Account views — auth, profile, card vault, @whyd.xyz email."""
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from .serializers import (
    LoginSerializer,
    PaymentMethodSerializer,
    RegisterSerializer,
    TCOProfileSerializer,
    UserSerializer,
    WhydudEmailSerializer,
)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2
        raise NotImplementedError


class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2
        raise NotImplementedError


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2
        raise NotImplementedError


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = UserSerializer(request.user)
        return success_response(serializer.data)

    def delete(self, request: Request) -> Response:
        # TODO Sprint 4: DPDP-compliant account deletion
        raise NotImplementedError


class WhydudEmailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2: Create @whyd.xyz email
        raise NotImplementedError

    def get(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2: Email status
        raise NotImplementedError


class WhydudEmailAvailabilityView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        # TODO Sprint 1 Week 2
        raise NotImplementedError


class PaymentMethodListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError

    def post(self, request: Request) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError


class PaymentMethodDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request: Request, pk: str) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError

    def delete(self, request: Request, pk: str) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError
