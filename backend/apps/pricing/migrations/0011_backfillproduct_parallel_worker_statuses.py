# Add intermediate status choices for parallel worker support.
# bh_filling: worker has claimed item for BuyHatke Phase 2
# ph_extending: worker has claimed item for PriceHistory Phase 3

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pricing', '0010_backfillproduct_current_price_category_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='backfillproduct',
            name='status',
            field=models.CharField(
                choices=[
                    ('discovered', 'Discovered'),
                    ('bh_filling', 'BH Filling'),
                    ('bh_filled', 'BuyHatke Filled'),
                    ('ph_extending', 'PH Extending'),
                    ('ph_extended', 'PH Extended'),
                    ('done', 'Done'),
                    ('failed', 'Failed'),
                    ('skipped', 'Skipped'),
                ],
                default='discovered',
                max_length=20,
            ),
        ),
    ]
