"""Serializers for the TCO app."""
from rest_framework import serializers

from .models import CityReferenceData, TCOModel, UserTCOProfile


class CitySerializer(serializers.ModelSerializer):
    class Meta:
        model = CityReferenceData
        fields = [
            "id", "city_name", "state",
            "electricity_tariff_residential", "cooling_days_per_year",
            "humidity_level", "water_tariff_per_kl", "water_hardness",
        ]


class TCOModelSerializer(serializers.ModelSerializer):
    category_slug = serializers.CharField(source="category.slug", read_only=True)

    class Meta:
        model = TCOModel
        fields = [
            "id", "category_slug", "name", "version",
            "input_schema", "cost_components",
        ]


class UserTCOProfileSerializer(serializers.ModelSerializer):
    city = CitySerializer(read_only=True)
    city_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = UserTCOProfile
        fields = [
            "city", "city_id",
            "electricity_tariff_override",
            "ac_hours_per_day", "ownership_years",
        ]


class TCOCalculateSerializer(serializers.Serializer):
    product_slug = serializers.CharField()
    city_id = serializers.IntegerField(required=False, allow_null=True)
    electricity_tariff = serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True)
    ac_hours_per_day = serializers.IntegerField(required=False, allow_null=True, min_value=0, max_value=24)
    ownership_years = serializers.IntegerField(required=False, default=5, min_value=1, max_value=20)
    inputs = serializers.DictField(required=False, default=dict)
