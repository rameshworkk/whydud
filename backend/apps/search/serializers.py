from rest_framework import serializers

class SearchResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    slug = serializers.CharField()
    title = serializers.CharField()
    brand_name = serializers.CharField()
    category_name = serializers.CharField()
    dud_score = serializers.DecimalField(max_digits=5, decimal_places=2, allow_null=True)
    current_best_price = serializers.DecimalField(max_digits=12, decimal_places=2, allow_null=True)
    image_url = serializers.URLField(allow_null=True)

class AutocompleteResultSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    slug = serializers.CharField()
    category_name = serializers.CharField()
