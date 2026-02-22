"""Search app has no Django models — uses Meilisearch as its datastore.

SearchLog model for analytics only.
"""
from django.db import models

class SearchLog(models.Model):
    """Anonymized search query log for analytics (retain 90 days)."""
    query = models.CharField(max_length=500)
    results_count = models.IntegerField(default=0)
    latency_ms = models.IntegerField(null=True, blank=True)
    filters_used = models.JSONField(default=dict)
    user_id = models.UUIDField(null=True, blank=True)  # nullable for anonymous
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "search_logs"
        ordering = ["-created_at"]
