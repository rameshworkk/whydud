from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("pricing", "0006_backfillproduct"),
    ]

    operations = [
        migrations.AddField(
            model_name="backfillproduct",
            name="raw_price_data",
            field=models.JSONField(
                default=list,
                blank=True,
                help_text="Cached raw price points: [{t, p, s}, ...]",
            ),
        ),
    ]
