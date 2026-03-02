"""Admin tooling models — audit logs, moderation queue, scraper runs, site config."""
import uuid

from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    """Immutable record of every admin action for compliance and debugging."""

    class Action(models.TextChoices):
        CREATE = "create", "Create"
        UPDATE = "update", "Update"
        DELETE = "delete", "Delete"
        APPROVE = "approve", "Approve"
        REJECT = "reject", "Reject"
        SUSPEND = "suspend", "Suspend"
        RESTORE = "restore", "Restore"
        CONFIG_CHANGE = "config_change", "Config Change"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=30, choices=Action.choices)
    target_type = models.CharField(max_length=100, help_text="App label + model name, e.g. 'reviews.Review'")
    target_id = models.CharField(max_length=255, help_text="PK of the affected object")
    old_value = models.JSONField(default=dict, blank=True)
    new_value = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin"."audit_logs'
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}:{self.target_id} by {self.admin_user_id}"


class ModerationQueue(models.Model):
    """Queue of items (reviews, discussions, users) awaiting moderator action."""

    class ItemType(models.TextChoices):
        REVIEW = "review", "Review"
        DISCUSSION = "discussion", "Discussion"
        USER = "user", "User"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item_type = models.CharField(max_length=20, choices=ItemType.choices)
    item_id = models.CharField(max_length=255, help_text="PK of the flagged object")
    reason = models.TextField(help_text="Why the item was flagged")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="moderation_assignments",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin"."moderation_queue'
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.item_type}:{self.item_id} [{self.status}]"


class ScraperRun(models.Model):
    """
    Aggregated record of a scraper execution.

    Complements scraping.ScraperJob (per-job tracking) with higher-level
    run-level stats useful for the admin dashboard.
    """

    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        PARTIAL = "partial", "Partial"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    marketplace = models.ForeignKey("products.Marketplace", on_delete=models.CASCADE)
    spider_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RUNNING)
    items_scraped = models.IntegerField(default=0)
    items_created = models.IntegerField(default=0)
    items_updated = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True, help_text="List of error dicts")
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'admin"."scraper_runs'
        ordering = ["-started_at"]

    def __str__(self) -> str:
        return f"{self.spider_name} @ {self.marketplace} [{self.status}]"

    @property
    def error_count(self) -> int:
        """Number of errors recorded for this run."""
        return len(self.errors) if isinstance(self.errors, list) else 0

    @property
    def duration_seconds(self) -> int | None:
        """Wall-clock duration in seconds, or None if still running."""
        if self.completed_at and self.started_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None


class SiteConfig(models.Model):
    """
    Key-value store for runtime-tuneable site configuration.

    Intended for values that admins adjust without a deploy — feature flags,
    rate limits, display settings, etc. Backed by JSONB for flexibility.
    """

    key = models.CharField(max_length=255, unique=True, help_text="Dot-separated config key, e.g. 'scoring.dudscore_version'")
    value = models.JSONField(help_text="Configuration value (any JSON-serialisable type)")
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="site_config_changes",
    )
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin"."site_config'
        ordering = ["key"]

    def __str__(self) -> str:
        return self.key
