from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class DealListView(APIView):
    permission_classes = [AllowAny]
    def get(self, request: Request) -> Response:
        # TODO Sprint 4 Week 10
        raise NotImplementedError

class DealDetailView(APIView):
    permission_classes = [AllowAny]
    def get(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class DealClickView(APIView):
    permission_classes = [AllowAny]
    def post(self, request: Request, pk: str) -> Response:
        # TODO: track affiliate click
        raise NotImplementedError
