from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0007_backfillproduct_raw_price_data"),
    ]

    operations = [
        migrations.AddField(
            model_name="backfillproduct",
            name="scrape_status",
            field=models.CharField(
                max_length=20,
                default="pending",
                choices=[
                    ("pending", "Pending"),
                    ("scraped", "Scraped"),
                    ("failed", "Failed"),
                ],
            ),
        ),
    ]
