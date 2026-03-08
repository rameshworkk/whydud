"""Add extended fields to Product and ProductListing.

Product: country_of_origin, manufacturer, model_number, weight, dimensions
ProductListing: variant_options, offer_details, about_bullets, warranty,
                delivery_info, return_policy

All fields are optional with defaults — no existing data affected.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("products", "0006_add_is_lightweight"),
    ]

    operations = [
        # --- Product fields (canonical, cross-marketplace) ---
        migrations.AddField(
            model_name="product",
            name="country_of_origin",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="manufacturer",
            field=models.CharField(max_length=500, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="model_number",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="weight",
            field=models.CharField(max_length=100, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="product",
            name="dimensions",
            field=models.CharField(max_length=200, blank=True, default=""),
        ),
        # --- ProductListing fields (per-marketplace detail) ---
        migrations.AddField(
            model_name="productlisting",
            name="variant_options",
            field=models.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="productlisting",
            name="offer_details",
            field=models.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="productlisting",
            name="about_bullets",
            field=models.JSONField(null=True, blank=True),
        ),
        migrations.AddField(
            model_name="productlisting",
            name="warranty",
            field=models.CharField(max_length=500, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="productlisting",
            name="delivery_info",
            field=models.CharField(max_length=500, blank=True, default=""),
        ),
        migrations.AddField(
            model_name="productlisting",
            name="return_policy",
            field=models.CharField(max_length=500, blank=True, default=""),
        ),
    ]
