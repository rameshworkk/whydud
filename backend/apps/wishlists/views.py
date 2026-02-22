from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class WishlistListCreateView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request: Request) -> Response:
        # TODO Sprint 3 Week 9
        raise NotImplementedError
    def post(self, request: Request) -> Response:
        raise NotImplementedError

class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]
    def patch(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
    def delete(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class WishlistItemView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
    def delete(self, request: Request, pk: str, product_id: str) -> Response:
        raise NotImplementedError
    def patch(self, request: Request, pk: str, product_id: str) -> Response:
        raise NotImplementedError

class PublicWishlistView(APIView):
    def get(self, request: Request, slug: str) -> Response:
        raise NotImplementedError
