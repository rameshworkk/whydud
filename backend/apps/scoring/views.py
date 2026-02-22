from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response

class DudScoreConfigView(APIView):
    """Admin-only: view and update DudScore weights."""
    def get(self, request: Request) -> Response:
        # TODO Sprint 3 Week 7
        raise NotImplementedError
