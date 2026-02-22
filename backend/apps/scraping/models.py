"""Scraping job tracking models."""
import uuid
from django.db import models

class ScraperJob(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.CASCADE)
    spider_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    items_scraped = models.IntegerField(default=0)
    items_failed = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    triggered_by = models.CharField(max_length=30, default="scheduled")  # scheduled | adhoc
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "scraper_jobs"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.spider_name} [{self.status}]"
