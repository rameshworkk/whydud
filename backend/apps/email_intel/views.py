from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from common.permissions import IsConnectedUser

class InboxListView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        # TODO Sprint 3 Week 8
        raise NotImplementedError

class InboxDetailView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request, pk: str) -> Response:
        # TODO Sprint 3 Week 8
        raise NotImplementedError
    def patch(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
    def delete(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class InboxReparseView(APIView):
    permission_classes = [IsConnectedUser]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class PurchaseDashboardView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        # TODO Sprint 3 Week 8
        raise NotImplementedError

class PurchaseListView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class RefundsView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class ReturnWindowsView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class SubscriptionsView(APIView):
    permission_classes = [IsConnectedUser]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class InboundEmailWebhookView(APIView):
    """Cloudflare Email Worker -> Django. HMAC-signed."""
    authentication_classes = []
    permission_classes = []
    def post(self, request: Request) -> Response:
        # TODO Sprint 3 Week 8: validate HMAC, enqueue Celery task
        raise NotImplementedError

class RazorpayWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    def post(self, request: Request) -> Response:
        # TODO Sprint 4
        raise NotImplementedError
