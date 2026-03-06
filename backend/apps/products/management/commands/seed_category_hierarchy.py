"""Seed the canonical 3-level category hierarchy.

Usage:
    python manage.py seed_category_hierarchy
    python manage.py seed_category_hierarchy --dry-run
"""
from django.core.management.base import BaseCommand

from apps.products.models import Category


# ---------------------------------------------------------------------------
# Canonical taxonomy: (name, slug, icon, children)
# ---------------------------------------------------------------------------

TAXONOMY = [
    ("Electronics", "electronics", "cpu", [
        ("Mobiles & Tablets", "mobiles-tablets", "smartphone", [
            ("Smartphones", "smartphones", "smartphone"),
            ("Feature Phones", "feature-phones", "phone"),
            ("Tablets", "tablets", "tablet-smartphone"),
            ("Mobile Accessories", "mobile-accessories", "cable"),
        ]),
        ("Computers & Peripherals", "computers-peripherals", "monitor", [
            ("Laptops", "laptops", "laptop"),
            ("Desktops", "desktops", "pc-case"),
            ("Monitors", "monitors", "monitor"),
            ("Printers & Scanners", "printers-scanners", "printer"),
            ("Networking", "networking", "wifi"),
            ("Computer Accessories", "computer-accessories", "keyboard"),
            ("Storage Devices", "storage-devices", "hard-drive"),
        ]),
        ("Audio", "audio", "headphones", [
            ("Headphones", "headphones", "headphones"),
            ("Earphones & Earbuds", "earphones-earbuds", "ear"),
            ("Speakers", "speakers", "speaker"),
            ("Soundbars", "soundbars", "volume-2"),
        ]),
        ("Television & Home Entertainment", "tv-home-entertainment", "tv", [
            ("Televisions", "televisions", "tv"),
            ("Streaming Devices", "streaming-devices", "cast"),
            ("Projectors", "projectors", "projector"),
        ]),
        ("Cameras & Photography", "cameras-photography", "camera", [
            ("DSLR & Mirrorless", "dslr-mirrorless", "camera"),
            ("Action Cameras", "action-cameras", "video"),
            ("Camera Accessories", "camera-accessories", "aperture"),
        ]),
        ("Wearables", "wearables", "watch", [
            ("Smartwatches", "smartwatches", "watch"),
            ("Fitness Bands", "fitness-bands", "activity"),
        ]),
        ("Gaming", "gaming", "gamepad-2", [
            ("Gaming Consoles", "gaming-consoles", "gamepad-2"),
            ("Gaming Laptops", "gaming-laptops", "laptop"),
            ("Gaming Accessories", "gaming-accessories", "joystick"),
            ("Video Games", "video-games", "disc"),
        ]),
    ]),
    ("Home & Living", "home-living", "home", [
        ("Kitchen", "kitchen", "utensils", [
            ("Cookware", "cookware", "cooking-pot"),
            ("Kitchen Appliances", "kitchen-appliances", "microwave"),
            ("Kitchen Storage", "kitchen-storage", "package"),
            ("Kitchen Tools", "kitchen-tools", "utensils"),
            ("Dinnerware", "dinnerware", "utensils-crossed"),
        ]),
        ("Home Appliances", "home-appliances", "fan", [
            ("Air Conditioners", "air-conditioners", "snowflake"),
            ("Refrigerators", "refrigerators", "thermometer-snowflake"),
            ("Washing Machines", "washing-machines", "washing-machine"),
            ("Water Purifiers", "water-purifiers", "droplets"),
            ("Air Purifiers", "air-purifiers", "wind"),
            ("Vacuum Cleaners", "vacuum-cleaners", "sparkles"),
            ("Fans & Coolers", "fans-coolers", "fan"),
            ("Geysers & Heaters", "geysers-heaters", "flame"),
            ("Irons & Steamers", "irons-steamers", "shirt"),
        ]),
        ("Furniture", "furniture", "sofa", [
            ("Living Room Furniture", "living-room-furniture", "sofa"),
            ("Bedroom Furniture", "bedroom-furniture", "bed-double"),
            ("Office Furniture", "office-furniture", "armchair"),
            ("Storage Furniture", "storage-furniture", "archive"),
        ]),
        ("Home Decor", "home-decor", "lamp", [
            ("Lighting", "lighting", "lamp"),
            ("Clocks", "clocks", "clock"),
            ("Wall Art", "wall-art", "frame"),
            ("Showpieces", "showpieces", "gem"),
        ]),
        ("Garden & Outdoor", "garden-outdoor", "flower-2", [
            ("Indoor Plants", "indoor-plants", "leaf"),
            ("Pots & Planters", "pots-planters", "flower-2"),
            ("Garden Tools", "garden-tools", "shovel"),
            ("Outdoor Furniture", "outdoor-furniture", "armchair"),
        ]),
        ("Bedding & Bath", "bedding-bath", "bed-double", [
            ("Bedsheets", "bedsheets", "bed-double"),
            ("Towels", "towels", "bath"),
            ("Pillows & Cushions", "pillows-cushions", "pillow"),
            ("Bathroom Accessories", "bathroom-accessories", "bath"),
        ]),
    ]),
    ("Appliances", "appliances", "plug", [
        ("Personal Care Appliances", "personal-care-appliances", "scissors", [
            ("Trimmers & Shavers", "trimmers-shavers", "scissors"),
            ("Hair Dryers & Stylers", "hair-dryers-stylers", "wind"),
            ("Electric Toothbrushes", "electric-toothbrushes", "smile"),
        ]),
        ("Small Appliances", "small-appliances", "zap", [
            ("Mixer Grinders", "mixer-grinders", "blend"),
            ("Induction Cooktops", "induction-cooktops", "flame"),
            ("Electric Kettles", "electric-kettles", "cup-soda"),
            ("Sandwich Makers & Grills", "sandwich-makers-grills", "sandwich"),
            ("Microwave Ovens", "microwave-ovens", "microwave"),
            ("OTGs", "otgs", "oven"),
        ]),
    ]),
    ("Fashion", "fashion", "shirt", [
        ("Men's Fashion", "mens-fashion", "shirt", [
            ("Men's T-Shirts", "mens-tshirts", "shirt"),
            ("Men's Shirts", "mens-shirts", "shirt"),
            ("Men's Jeans & Trousers", "mens-jeans-trousers", "ruler"),
            ("Men's Shoes", "mens-shoes", "footprints"),
            ("Men's Watches", "mens-watches", "watch"),
            ("Men's Accessories", "mens-accessories", "glasses"),
        ]),
        ("Women's Fashion", "womens-fashion", "shirt", [
            ("Women's Ethnic Wear", "womens-ethnic-wear", "shirt"),
            ("Women's Western Wear", "womens-western-wear", "shirt"),
            ("Women's Shoes", "womens-shoes", "footprints"),
            ("Women's Watches", "womens-watches", "watch"),
            ("Women's Handbags", "womens-handbags", "briefcase"),
            ("Women's Jewellery", "womens-jewellery", "gem"),
        ]),
        ("Kids' Fashion", "kids-fashion", "baby", [
            ("Boys' Clothing", "boys-clothing", "shirt"),
            ("Girls' Clothing", "girls-clothing", "shirt"),
            ("Kids' Shoes", "kids-shoes", "footprints"),
        ]),
        ("Bags & Luggage", "bags-luggage", "briefcase", [
            ("Backpacks", "backpacks", "backpack"),
            ("Suitcases", "suitcases", "luggage"),
            ("Wallets", "wallets", "wallet"),
        ]),
    ]),
    ("Beauty & Personal Care", "beauty-personal-care", "sparkles", [
        ("Skincare", "skincare", "droplet", [
            ("Face Care", "face-care", "smile"),
            ("Body Care", "body-care", "sparkles"),
            ("Sunscreen", "sunscreen", "sun"),
        ]),
        ("Haircare", "haircare", "scissors", [
            ("Shampoo & Conditioner", "shampoo-conditioner", "droplets"),
            ("Hair Oil", "hair-oil", "droplet"),
            ("Hair Styling", "hair-styling", "wand"),
        ]),
        ("Makeup", "makeup", "palette", [
            ("Lipstick & Lip Care", "lipstick-lip-care", "heart"),
            ("Foundation & Face", "foundation-face", "circle"),
            ("Eye Makeup", "eye-makeup", "eye"),
        ]),
        ("Fragrances", "fragrances", "spray-can", [
            ("Perfumes", "perfumes", "spray-can"),
            ("Deodorants", "deodorants", "spray-can"),
        ]),
    ]),
    ("Health & Wellness", "health-wellness", "heart-pulse", [
        ("Nutrition & Supplements", "nutrition-supplements", "apple", [
            ("Protein & Fitness", "protein-fitness", "dumbbell"),
            ("Vitamins & Minerals", "vitamins-minerals", "pill"),
            ("Ayurveda", "ayurveda", "leaf"),
        ]),
        ("Medical Devices", "medical-devices", "stethoscope", [
            ("BP Monitors", "bp-monitors", "heart-pulse"),
            ("Glucometers", "glucometers", "droplet"),
            ("Oximeters", "oximeters", "activity"),
        ]),
    ]),
    ("Sports & Fitness", "sports-fitness", "dumbbell", [
        ("Exercise & Fitness", "exercise-fitness", "dumbbell", [
            ("Treadmills & Cycles", "treadmills-cycles", "bike"),
            ("Yoga & Accessories", "yoga-accessories", "stretch-horizontal"),
            ("Dumbbells & Weights", "dumbbells-weights", "dumbbell"),
        ]),
        ("Sports Equipment", "sports-equipment", "trophy", [
            ("Cricket", "cricket", "circle-dot"),
            ("Badminton", "badminton", "circle-dot"),
            ("Football", "football", "circle"),
        ]),
    ]),
    ("Books & Stationery", "books-stationery", "book-open", [
        ("Books", "books", "book-open", [
            ("Fiction", "fiction", "book"),
            ("Non-Fiction", "non-fiction", "book-open"),
            ("Academic & Competitive", "academic-competitive", "graduation-cap"),
            ("Children's Books", "childrens-books", "baby"),
        ]),
        ("Stationery & Office", "stationery-office", "pen-tool", [
            ("Writing Instruments", "writing-instruments", "pen"),
            ("Office Supplies", "office-supplies", "paperclip"),
        ]),
    ]),
    ("Baby & Kids", "baby-kids", "baby", [
        ("Baby Care", "baby-care", "baby", [
            ("Diapers & Wipes", "diapers-wipes", "baby"),
            ("Baby Food & Formula", "baby-food-formula", "milk"),
            ("Baby Bathing", "baby-bathing", "bath"),
        ]),
        ("Toys & Games", "toys-games", "puzzle", [
            ("Educational Toys", "educational-toys", "blocks"),
            ("Action Figures", "action-figures", "swords"),
            ("Board Games", "board-games", "dice-5"),
        ]),
        ("Baby Gear", "baby-gear", "car", [
            ("Strollers", "strollers", "baby"),
            ("Car Seats", "car-seats", "car"),
        ]),
    ]),
    ("Automotive", "automotive", "car", [
        ("Car Accessories", "car-accessories", "car", [
            ("Car Electronics", "car-electronics", "radio"),
            ("Car Care", "car-care", "droplets"),
        ]),
        ("Bike Accessories", "bike-accessories", "bike", [
            ("Helmets", "helmets", "hard-hat"),
            ("Bike Care", "bike-care", "wrench"),
        ]),
    ]),
    ("Pet Supplies", "pet-supplies", "paw-print", [
        ("Dog Supplies", "dog-supplies", "dog", [
            ("Dog Food", "dog-food", "bone"),
            ("Dog Accessories", "dog-accessories", "paw-print"),
        ]),
        ("Cat Supplies", "cat-supplies", "cat", [
            ("Cat Food", "cat-food", "fish"),
            ("Cat Accessories", "cat-accessories", "paw-print"),
        ]),
    ]),
    ("Musical Instruments", "musical-instruments", "music", [
        ("Guitars", "guitars", "guitar", [
            ("Acoustic Guitars", "acoustic-guitars", "guitar"),
            ("Electric Guitars", "electric-guitars", "guitar"),
        ]),
        ("Keyboards & Pianos", "keyboards-pianos", "piano", [
            ("Keyboards", "keyboards-music", "piano"),
            ("Digital Pianos", "digital-pianos", "piano"),
        ]),
    ]),
]


class Command(BaseCommand):
    help = "Seed the canonical 3-level category hierarchy"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print the tree without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made\n"))
            self._print_taxonomy()
            return

        dept_count = 0
        cat_count = 0
        sub_count = 0

        # Known department slugs for orphan detection
        dept_slugs = [dept[1] for dept in TAXONOMY]

        for dept_name, dept_slug, dept_icon, categories in TAXONOMY:
            dept, _ = Category.objects.update_or_create(
                slug=dept_slug,
                defaults={
                    "name": dept_name,
                    "level": 0,
                    "parent": None,
                    "icon": dept_icon,
                    "is_active": True,
                    "display_order": dept_count,
                },
            )
            dept_count += 1

            for cat_idx, (cat_name, cat_slug, cat_icon, subcategories) in enumerate(categories):
                cat, _ = Category.objects.update_or_create(
                    slug=cat_slug,
                    defaults={
                        "name": cat_name,
                        "level": 1,
                        "parent": dept,
                        "icon": cat_icon,
                        "is_active": True,
                        "display_order": cat_idx,
                    },
                )
                cat_count += 1

                for sub_idx, (sub_name, sub_slug, sub_icon) in enumerate(subcategories):
                    Category.objects.update_or_create(
                        slug=sub_slug,
                        defaults={
                            "name": sub_name,
                            "level": 2,
                            "parent": cat,
                            "icon": sub_icon,
                            "is_active": True,
                            "display_order": sub_idx,
                        },
                    )
                    sub_count += 1

        self.stdout.write(self.style.SUCCESS(
            f"\nSeeded: {dept_count} departments, {cat_count} categories, {sub_count} subcategories"
        ))

        # Recalculate product_count at all levels
        self.stdout.write("\nRecalculating product counts...")
        self._recalculate_product_counts()

        # Print the tree
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("CATEGORY TREE")
        self.stdout.write("=" * 60)
        for dept in Category.objects.filter(level=0).order_by("display_order", "name"):
            self.stdout.write(f"\n{dept.name} ({dept.product_count} products)")
            for cat in dept.children.order_by("display_order", "name"):
                self.stdout.write(f"  +-- {cat.name} ({cat.product_count})")
                for sub in cat.children.order_by("display_order", "name"):
                    self.stdout.write(f"  |   +-- {sub.name} ({sub.product_count})")

        # Check for orphan categories
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("ORPHAN CHECK")
        self.stdout.write("=" * 60)
        orphans = Category.objects.filter(
            parent__isnull=True, level=0
        ).exclude(slug__in=dept_slugs)
        if orphans.exists():
            for o in orphans:
                prod_count = o.products.count()
                self.stdout.write(self.style.WARNING(
                    f"  ORPHAN: {o.slug} ({o.name}) - {prod_count} products"
                ))
        else:
            self.stdout.write(self.style.SUCCESS("  No orphan categories found."))

    def _recalculate_product_counts(self):
        """Recalculate product_count at all levels bottom-up."""
        # Leaf categories: direct product count
        for cat in Category.objects.filter(level=2):
            cat.product_count = cat.products.filter(status="active").count()
            cat.save(update_fields=["product_count"])

        # Mid-level: sum of children
        for cat in Category.objects.filter(level=1):
            cat.product_count = sum(c.product_count for c in cat.children.all())
            cat.save(update_fields=["product_count"])

        # Departments: sum of children
        for cat in Category.objects.filter(level=0):
            cat.product_count = sum(c.product_count for c in cat.children.all())
            cat.save(update_fields=["product_count"])

    def _print_taxonomy(self):
        """Print the taxonomy tree without touching the DB."""
        for dept_name, dept_slug, _, categories in TAXONOMY:
            self.stdout.write(f"\n{dept_name} (slug={dept_slug})")
            for cat_name, cat_slug, _, subcategories in categories:
                self.stdout.write(f"  +-- {cat_name} (slug={cat_slug})")
                for sub_name, sub_slug, _ in subcategories:
                    self.stdout.write(f"  |   +-- {sub_name} (slug={sub_slug})")
