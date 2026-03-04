# Email parsing pipeline — add delivery/otp categories and failed_permanent status

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("email_intel", "0003_emailsource"),
    ]

    operations = [
        migrations.AlterField(
            model_name="inboxemail",
            name="category",
            field=models.CharField(
                blank=True,
                choices=[
                    ("order", "Order"),
                    ("shipping", "Shipping"),
                    ("delivery", "Delivery"),
                    ("refund", "Refund"),
                    ("return", "Return"),
                    ("subscription", "Subscription"),
                    ("promo", "Promotional"),
                    ("otp", "OTP / Verification"),
                    ("other", "Other"),
                ],
                max_length=30,
            ),
        ),
        migrations.AlterField(
            model_name="inboxemail",
            name="parse_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"),
                    ("parsed", "Parsed"),
                    ("failed", "Failed"),
                    ("failed_permanent", "Failed Permanently"),
                    ("skipped", "Skipped"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
