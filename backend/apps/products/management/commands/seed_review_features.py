"""Seed review_features into Category.spec_schema for feature-specific ratings.

Merges {"review_features": [...]} into each category's existing spec_schema
JSONField. Existing spec_schema keys are preserved.

Usage:
    python manage.py seed_review_features
    python manage.py seed_review_features --flush   # Remove review_features from all categories

Consumed by:
    GET /api/v1/reviews/product/:slug/features  →  ReviewFeaturesView (reviews/views.py)
"""

from django.core.management.base import BaseCommand

from apps.products.models import Category


# ---------------------------------------------------------------------------
# Review features per category
# Each entry: (category_slug, [{"key": ..., "label": ...}, ...])
# ---------------------------------------------------------------------------

REVIEW_FEATURES: list[tuple[str, list[dict[str, str]]]] = [
    # ── Phones / Smartphones ──────────────────────────────────────────────
    (
        "phones",
        [
            {"key": "style_design", "label": "Style & Design"},
            {"key": "battery_life", "label": "Battery Life"},
            {"key": "user_friendliness", "label": "User Friendliness"},
            {"key": "performance", "label": "Performance"},
            {"key": "camera_quality", "label": "Camera Quality"},
            {"key": "value_for_money", "label": "Value for Money"},
            {"key": "durability", "label": "Durability"},
        ],
    ),
    # ── Air Conditioners ──────────────────────────────────────────────────
    (
        "air-conditioners",
        [
            {"key": "cooling", "label": "Cooling"},
            {"key": "energy_efficiency", "label": "Energy Efficiency"},
            {"key": "noise", "label": "Noise"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "smart_features", "label": "Smart Features"},
            {"key": "installation", "label": "Installation"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Air Purifiers ─────────────────────────────────────────────────────
    (
        "air-purifiers",
        [
            {"key": "filtration", "label": "Filtration"},
            {"key": "noise", "label": "Noise"},
            {"key": "coverage", "label": "Coverage"},
            {"key": "filter_life", "label": "Filter Life"},
            {"key": "smart_features", "label": "Smart Features"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Water Purifiers ───────────────────────────────────────────────────
    (
        "water-purifiers",
        [
            {"key": "purification_quality", "label": "Purification Quality"},
            {"key": "taste", "label": "Taste"},
            {"key": "flow_rate", "label": "Flow Rate"},
            {"key": "filter_life", "label": "Filter Life"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Refrigerators ─────────────────────────────────────────────────────
    (
        "refrigerators",
        [
            {"key": "cooling", "label": "Cooling"},
            {"key": "energy_efficiency", "label": "Energy Efficiency"},
            {"key": "storage_capacity", "label": "Storage & Capacity"},
            {"key": "noise", "label": "Noise"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Washing Machines ──────────────────────────────────────────────────
    (
        "washing-machines",
        [
            {"key": "wash_quality", "label": "Wash Quality"},
            {"key": "energy_efficiency", "label": "Energy Efficiency"},
            {"key": "noise", "label": "Noise"},
            {"key": "ease_of_use", "label": "Ease of Use"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Laptops ───────────────────────────────────────────────────────────
    (
        "laptops",
        [
            {"key": "performance", "label": "Performance"},
            {"key": "display", "label": "Display"},
            {"key": "battery_life", "label": "Battery Life"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "keyboard_trackpad", "label": "Keyboard & Trackpad"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
    # ── Vehicles ──────────────────────────────────────────────────────────
    (
        "vehicles",
        [
            {"key": "ride_comfort", "label": "Ride Comfort"},
            {"key": "performance", "label": "Performance"},
            {"key": "fuel_efficiency", "label": "Fuel Efficiency"},
            {"key": "build_quality", "label": "Build Quality"},
            {"key": "features", "label": "Features"},
            {"key": "after_sales", "label": "After-Sales Service"},
            {"key": "value_for_money", "label": "Value for Money"},
        ],
    ),
]


class Command(BaseCommand):
    help = "Seed review_features into Category.spec_schema for feature-specific ratings"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Remove review_features key from all categories' spec_schema.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            count = 0
            for cat in Category.objects.exclude(spec_schema=None):
                schema = cat.spec_schema or {}
                if "review_features" in schema:
                    del schema["review_features"]
                    cat.spec_schema = schema if schema else None
                    cat.save(update_fields=["spec_schema"])
                    count += 1
            self.stdout.write(self.style.WARNING(f"Removed review_features from {count} category(ies)."))
            return

        updated_count = 0
        created_count = 0

        for slug, features in REVIEW_FEATURES:
            category, cat_created = Category.objects.get_or_create(
                slug=slug,
                defaults={"name": slug.replace("-", " ").title(), "level": 0},
            )
            if cat_created:
                self.stdout.write(f"  Created category: {category.name} ({slug})")
                created_count += 1

            # Merge into existing spec_schema (preserve other keys)
            schema = category.spec_schema or {}
            schema["review_features"] = features
            category.spec_schema = schema
            category.save(update_fields=["spec_schema"])

            feature_count = len(features)
            self.stdout.write(self.style.SUCCESS(
                f"  {slug}: {feature_count} review features"
            ))
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nDone. {updated_count} categories updated"
            + (f", {created_count} new categories created." if created_count else ".")
        ))
