"""TCO views."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from apps.products.models import Category
from .models import CityReferenceData, TCOModel, UserTCOProfile
from .serializers import CitySerializer, TCOModelSerializer, UserTCOProfileSerializer


class CityListView(APIView):
    """GET /api/v1/tco/cities"""
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        state = request.query_params.get("state")
        qs = CityReferenceData.objects.order_by("state", "city_name")
        if state:
            qs = qs.filter(state__icontains=state)
        return success_response(CitySerializer(qs, many=True).data)


class TCOModelView(APIView):
    """GET /api/v1/tco/models/:category_slug"""
    permission_classes = [AllowAny]

    def get(self, request: Request, category_slug: str) -> Response:
        category = get_object_or_404(Category, slug=category_slug, has_tco_model=True)
        tco_model = TCOModel.objects.filter(
            category=category, is_active=True
        ).order_by("-version").first()
        if not tco_model:
            return error_response("not_found", "No active TCO model for this category.", status=404)
        return success_response(TCOModelSerializer(tco_model).data)


class TCOProfileView(APIView):
    """PATCH /api/v1/tco/profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile, _ = UserTCOProfile.objects.get_or_create(user=request.user)
        return success_response(UserTCOProfileSerializer(profile).data)

    def patch(self, request: Request) -> Response:
        profile, _ = UserTCOProfile.objects.get_or_create(user=request.user)
        serializer = UserTCOProfileSerializer(profile, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)
