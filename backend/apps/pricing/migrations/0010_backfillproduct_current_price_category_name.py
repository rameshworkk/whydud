# Generated manually for BF-9

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0009_add_enrichment_review_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='backfillproduct',
            name='current_price',
            field=models.DecimalField(
                blank=True, decimal_places=2, max_digits=12, null=True,
                help_text='Latest known price in paisa (from tracker or raw_price_data)',
            ),
        ),
        migrations.AddField(
            model_name='backfillproduct',
            name='category_name',
            field=models.CharField(
                blank=True, db_index=True, max_length=100,
                help_text='Inferred from title via regex (e.g. smartphone, laptop, tv)',
            ),
        ),
    ]
