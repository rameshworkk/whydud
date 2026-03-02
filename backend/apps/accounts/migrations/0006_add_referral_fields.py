"""Add referral_code and referred_by to User model.

Three-step migration for the unique referral_code field:
1. Add fields (referral_code without unique constraint)
2. Populate existing rows with unique codes
3. Add unique constraint
"""
import secrets

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def generate_referral_codes(apps, schema_editor):
    """Backfill referral_code for all existing users."""
    User = apps.get_model("accounts", "User")
    used_codes = set()
    for user in User.objects.all().iterator():
        while True:
            code = secrets.token_hex(4).upper()
            if code not in used_codes:
                break
        used_codes.add(code)
        user.referral_code = code
        user.save(update_fields=["referral_code"])


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0005_purchasepreference"),
    ]

    operations = [
        # Step 1: Add fields without unique
        migrations.AddField(
            model_name="user",
            name="referral_code",
            field=models.CharField(default="", max_length=8),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="user",
            name="referred_by",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="referrals",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        # Step 2: Populate existing rows
        migrations.RunPython(generate_referral_codes, migrations.RunPython.noop),
        # Step 3: Add unique constraint
        migrations.AlterField(
            model_name="user",
            name="referral_code",
            field=models.CharField(
                default=secrets.token_hex,  # placeholder — real default is on model
                max_length=8,
                unique=True,
            ),
        ),
    ]
