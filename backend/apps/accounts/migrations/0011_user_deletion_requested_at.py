"""Add deletion_requested_at field to User for DPDP soft-delete."""

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0010_marketplace_preferences"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="deletion_requested_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
