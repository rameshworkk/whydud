"""Serializers for purchase preferences."""
from rest_framework import serializers

from apps.products.models import CategoryPreferenceSchema

from .models import PurchasePreference


class PurchasePreferenceSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = PurchasePreference
        fields = ["category_slug", "preferences", "updated_at"]
        read_only_fields = ["category_slug", "updated_at"]


class CategoryPreferenceSchemaSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = CategoryPreferenceSchema
        fields = ["category_slug", "schema", "version"]
        read_only_fields = fields
