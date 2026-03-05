"""Scoring views -- DudScore config + Brand Trust Scores."""
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.app_settings import BrandTrustConfig
from common.utils import error_response, success_response

from .models import BrandTrustScore, DudScoreConfig
from .serializers import BrandTrustScoreSerializer, DudScoreConfigSerializer


class ActiveDudScoreConfigView(APIView):
    """GET /api/v1/scoring/config -- current active DudScore weights."""
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        config = DudScoreConfig.objects.filter(is_active=True).order_by("-version").first()
        if not config:
            return error_response("not_found", "No active DudScore configuration.", status=404)
        return success_response(DudScoreConfigSerializer(config).data)


class BrandTrustScoreView(APIView):
    """GET /api/v1/brands/{slug}/trust-score -- trust score for a single brand."""
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        try:
            score = (
                BrandTrustScore.objects
                .select_related("brand")
                .get(brand__slug=slug)
            )
        except BrandTrustScore.DoesNotExist:
            return error_response(
                "not_found",
                "No trust score available for this brand.",
                status=404,
            )
        return success_response(BrandTrustScoreSerializer(score).data)


class BrandLeaderboardView(APIView):
    """GET /api/v1/brands/leaderboard -- top and bottom brands by trust score."""
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        limit = BrandTrustConfig.leaderboard_size()
        qs = BrandTrustScore.objects.select_related("brand")

        top = qs.order_by("-avg_dud_score")[:limit]
        bottom = qs.order_by("avg_dud_score")[:limit]

        return success_response({
            "top": BrandTrustScoreSerializer(top, many=True).data,
            "bottom": BrandTrustScoreSerializer(bottom, many=True).data,
        })
