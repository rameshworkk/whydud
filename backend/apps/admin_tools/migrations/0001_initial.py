# Generated manually for admin_tools app

import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("products", "0001_initial"),
    ]

    operations = [
        # Create the admin schema (other schemas created in accounts 0001)
        migrations.RunSQL(
            sql="CREATE SCHEMA IF NOT EXISTS admin;",
            reverse_sql="DROP SCHEMA IF EXISTS admin CASCADE;",
        ),
        # ── AuditLog ──────────────────────────────────────────────
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[
                    ("create", "Create"), ("update", "Update"), ("delete", "Delete"),
                    ("approve", "Approve"), ("reject", "Reject"), ("suspend", "Suspend"),
                    ("restore", "Restore"), ("config_change", "Config Change"),
                ], max_length=30)),
                ("target_type", models.CharField(help_text="App label + model name, e.g. 'reviews.Review'", max_length=100)),
                ("target_id", models.CharField(help_text="PK of the affected object", max_length=255)),
                ("old_value", models.JSONField(blank=True, default=dict)),
                ("new_value", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("admin_user", models.ForeignKey(
                    null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="audit_logs", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": 'admin"."audit_logs',
                "ordering": ["-created_at"],
            },
        ),
        # ── ModerationQueue ───────────────────────────────────────
        migrations.CreateModel(
            name="ModerationQueue",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("item_type", models.CharField(choices=[
                    ("review", "Review"), ("discussion", "Discussion"), ("user", "User"),
                ], max_length=20)),
                ("item_id", models.CharField(help_text="PK of the flagged object", max_length=255)),
                ("reason", models.TextField(help_text="Why the item was flagged")),
                ("status", models.CharField(choices=[
                    ("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"),
                ], default="pending", max_length=20)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("assigned_to", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="moderation_assignments", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": 'admin"."moderation_queue',
                "ordering": ["-created_at"],
            },
        ),
        # ── ScraperRun ────────────────────────────────────────────
        migrations.CreateModel(
            name="ScraperRun",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("spider_name", models.CharField(max_length=100)),
                ("status", models.CharField(choices=[
                    ("running", "Running"), ("completed", "Completed"),
                    ("failed", "Failed"), ("partial", "Partial"),
                ], default="running", max_length=20)),
                ("items_scraped", models.IntegerField(default=0)),
                ("items_created", models.IntegerField(default=0)),
                ("items_updated", models.IntegerField(default=0)),
                ("errors", models.JSONField(blank=True, default=list, help_text="List of error dicts")),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
                ("marketplace", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE, to="products.marketplace",
                )),
            ],
            options={
                "db_table": 'admin"."scraper_runs',
                "ordering": ["-started_at"],
            },
        ),
        # ── SiteConfig ────────────────────────────────────────────
        migrations.CreateModel(
            name="SiteConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(help_text="Dot-separated config key, e.g. 'scoring.dudscore_version'", max_length=255, unique=True)),
                ("value", models.JSONField(help_text="Configuration value (any JSON-serialisable type)")),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_by", models.ForeignKey(
                    blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                    related_name="site_config_changes", to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                "db_table": 'admin"."site_config',
                "ordering": ["key"],
            },
        ),
    ]
