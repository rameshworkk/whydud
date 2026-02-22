from rest_framework import serializers
from .models import ScraperJob

class ScraperJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ScraperJob
        fields = ["id", "marketplace", "spider_name", "status",
                  "started_at", "finished_at", "items_scraped",
                  "items_failed", "triggered_by", "created_at"]
        read_only_fields = ["id", "created_at"]
