"""Product views."""
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from .models import BankCard, Product
from .serializers import BankCardSerializer, ProductDetailSerializer, ProductSerializer


class ProductDetailView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 1 Week 3
        raise NotImplementedError


class ProductPriceHistoryView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 2 Week 5
        raise NotImplementedError


class ProductBestDealsView(APIView):
    """Personalized card × marketplace deal optimizer."""

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError


class ProductTCOView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 4 Week 10
        raise NotImplementedError


class ProductDiscussionsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 4 Week 11
        raise NotImplementedError


class CompareView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        # TODO Sprint 4 Week 10: ?slugs=slug1,slug2,slug3,slug4
        raise NotImplementedError


class BankListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        # TODO Sprint 3
        raise NotImplementedError


class BankCardVariantsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, bank_slug: str) -> Response:
        # TODO Sprint 3
        raise NotImplementedError
