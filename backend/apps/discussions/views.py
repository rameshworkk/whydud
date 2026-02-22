from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny

class CreateDiscussionView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, slug: str) -> Response:
        # TODO Sprint 4 Week 11
        raise NotImplementedError

class DiscussionDetailView(APIView):
    def get(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
    def patch(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
    def delete(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class DiscussionReplyView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class DiscussionVoteView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class ReplyAcceptView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError

class ReplyVoteView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request, pk: str) -> Response:
        raise NotImplementedError
