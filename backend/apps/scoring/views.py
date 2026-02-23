"""Scoring views -- DudScore config (read-only for public, admin writes via Django Admin)."""
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from .models import DudScoreConfig
from .serializers import DudScoreConfigSerializer


class ActiveDudScoreConfigView(APIView):
    """GET /api/v1/scoring/config -- current active DudScore weights."""
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        config = DudScoreConfig.objects.filter(is_active=True).order_by("-version").first()
        if not config:
            return error_response("not_found", "No active DudScore configuration.", status=404)
        return success_response(DudScoreConfigSerializer(config).data)
