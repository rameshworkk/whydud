# Add ORDER_DETECTED notification type for email parsing pipeline

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0008_seed_more_reserved_usernames"),
    ]

    operations = [
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("price_drop", "Price Drop"),
                    ("return_window", "Return Window"),
                    ("refund_delay", "Refund Delay"),
                    ("back_in_stock", "Back in Stock"),
                    ("review_upvote", "Review Upvote"),
                    ("price_alert", "Price Alert"),
                    ("discussion_reply", "Discussion Reply"),
                    ("level_up", "Level Up"),
                    ("points_earned", "Points Earned"),
                    ("subscription_renewal", "Subscription Renewal"),
                    ("order_detected", "Order Detected"),
                ],
                max_length=50,
            ),
        ),
    ]
