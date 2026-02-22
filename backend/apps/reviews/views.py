from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class ProductReviewsView(APIView):
    def get(self, request: Request, slug: str) -> Response:
        # TODO Sprint 2 Week 6
        raise NotImplementedError

class ReviewVoteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        # TODO Sprint 2 Week 6
        raise NotImplementedError

    def delete(self, request: Request, pk: str) -> Response:
        # TODO Sprint 2 Week 6
        raise NotImplementedError
