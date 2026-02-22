from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

class ActiveOffersView(APIView):
    def get(self, request: Request) -> Response:
        # TODO Sprint 3
        raise NotImplementedError

class EffectivePriceView(APIView):
    """Calculate personalized effective price given user's payment methods."""
    def get(self, request: Request, product_slug: str) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError
