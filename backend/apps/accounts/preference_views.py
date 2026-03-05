"""Purchase preference views — per-category questionnaire answers."""
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.products.models import Category, CategoryPreferenceSchema
from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import PurchasePreference
from .preference_serializers import (
    CategoryPreferenceSchemaSerializer,
    PurchasePreferenceSerializer,
)


class PreferenceListView(APIView):
    """GET /api/v1/preferences — all user's category preferences."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            PurchasePreference.objects.filter(user=request.user)
            .select_related("category")
            .order_by("-updated_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                PurchasePreferenceSerializer(page, many=True).data
            )
        return success_response(PurchasePreferenceSerializer(qs, many=True).data)


class PreferenceDetailView(APIView):
    """GET / POST / PATCH / DELETE  /api/v1/preferences/:category_slug."""

    permission_classes = [IsAuthenticated]

    def _get_category(self, slug: str) -> Category:
        return get_object_or_404(Category, slug=slug)

    def get(self, request: Request, category_slug: str) -> Response:
        category = self._get_category(category_slug)
        pref = PurchasePreference.objects.filter(
            user=request.user, category=category
        ).select_related("category").first()
        if not pref:
            return error_response("not_found", "No preferences saved for this category.", status=404)
        return success_response(PurchasePreferenceSerializer(pref).data)

    def post(self, request: Request, category_slug: str) -> Response:
        category = self._get_category(category_slug)
        if PurchasePreference.objects.filter(user=request.user, category=category).exists():
            return error_response(
                "already_exists",
                "Preferences already exist for this category. Use PATCH to update.",
            )
        serializer = PurchasePreferenceSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save(user=request.user, category=category)
        return success_response(serializer.data, status=201)

    def patch(self, request: Request, category_slug: str) -> Response:
        category = self._get_category(category_slug)
        pref = PurchasePreference.objects.filter(
            user=request.user, category=category
        ).select_related("category").first()
        if not pref:
            return error_response("not_found", "No preferences saved for this category.", status=404)
        serializer = PurchasePreferenceSerializer(pref, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, category_slug: str) -> Response:
        category = self._get_category(category_slug)
        deleted, _ = PurchasePreference.objects.filter(
            user=request.user, category=category
        ).delete()
        if not deleted:
            return error_response("not_found", "No preferences saved for this category.", status=404)
        return success_response({"detail": "Preferences removed."})


class PreferenceSchemaListView(APIView):
    """GET /api/v1/preferences/schemas — list all active category schemas."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        schemas = (
            CategoryPreferenceSchema.objects.filter(is_active=True)
            .select_related("category")
            .order_by("category__name")
        )
        return success_response(
            CategoryPreferenceSchemaSerializer(schemas, many=True).data
        )


class PreferenceSchemaView(APIView):
    """GET /api/v1/preferences/:category_slug/schema — questionnaire schema."""

    permission_classes = [AllowAny]

    def get(self, request: Request, category_slug: str) -> Response:
        category = get_object_or_404(Category, slug=category_slug)
        try:
            schema_obj = category.preference_schema
        except CategoryPreferenceSchema.DoesNotExist:
            return error_response(
                "not_found",
                "No preference schema defined for this category.",
                status=404,
            )
        return success_response(CategoryPreferenceSchemaSerializer(schema_obj).data)
