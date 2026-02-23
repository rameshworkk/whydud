"""Add weights_sum CHECK constraint to scoring.dudscore_config.

Enforces that the six DudScore weights must sum to exactly 1.0
(within floating-point tolerance of 0.001).
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("scoring", "0002_dudscore_history_hypertable"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE scoring.dudscore_config
                ADD CONSTRAINT weights_sum CHECK (
                    ABS(
                        w_sentiment + w_rating_quality + w_price_value +
                        w_review_credibility + w_price_stability + w_return_signal
                        - 1.0
                    ) < 0.001
                );
            """,
            reverse_sql="""
                ALTER TABLE scoring.dudscore_config
                DROP CONSTRAINT IF EXISTS weights_sum;
            """,
        ),
    ]
