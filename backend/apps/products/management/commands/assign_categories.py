"""Management command to auto-assign categories to products missing them.

Uses the canonical keyword mapper (273 keywords → level-2 subcategories) plus
regex fallback rules for broader matches.

Usage:
    python manage.py assign_categories          # assign + print summary
    python manage.py assign_categories --dry-run # preview without saving
    python manage.py assign_categories --force   # re-assign even if already categorized
    python manage.py assign_categories --reindex # also trigger Meilisearch reindex
"""
import re

from django.core.management.base import BaseCommand


# ---------------------------------------------------------------------------
# Fallback regex rules — broader patterns for products that don't match the
# canonical keyword mapper. Maps to level-2 subcategory slugs.
# ---------------------------------------------------------------------------

_FALLBACK_RULES: list[tuple[re.Pattern, str]] = [
    # Smartphones & mobile accessories
    (re.compile(
        r"\b(smartphone|mobile phone|iphone|galaxy [sazm]\d|redmi|realme \d|"
        r"oneplus \d|poco|pixel \d|vivo [tvyx]|oppo [afr]|iqoo|moto [gex]|"
        r"nothing phone|samsung galaxy [sazm]|nokia \d)"
        , re.IGNORECASE), "smartphones"),
    (re.compile(
        r"\b(phone case|phone cover|back cover|screen protector|tempered glass|"
        r"mobile charger|charging cable|usb[-\s]c cable|lightning cable|"
        r"car charger|wireless charger|phone holder|phone stand|phone grip|pop socket)"
        , re.IGNORECASE), "mobile-accessories"),
    (re.compile(
        r"\b(power bank|portable charger|battery pack)"
        , re.IGNORECASE), "mobile-accessories"),

    # Laptops (specific models)
    (re.compile(
        r"\b(laptop|notebook|macbook|chromebook|thinkpad|ideapad|vivobook|"
        r"zenbook|inspiron|pavilion|probook|elitebook|surface pro|surface laptop|"
        r"ultrabook)"
        , re.IGNORECASE), "laptops"),

    # Tablets
    (re.compile(
        r"\b(tablet|ipad|galaxy tab|fire\s*hd|kindle fire|lenovo tab|"
        r"realme pad|oneplus pad|xiaomi pad)"
        , re.IGNORECASE), "tablets"),

    # Audio
    (re.compile(
        r"\b(headphone|over.ear|on.ear|anc headphone|noise cancell)"
        , re.IGNORECASE), "headphones"),
    (re.compile(
        r"\b(earphone|earbud|earbuds|tws|neckband|true wireless|in.ear)"
        , re.IGNORECASE), "earphones-earbuds"),
    (re.compile(
        r"\b(bluetooth speaker|portable speaker|party speaker|smart speaker)"
        , re.IGNORECASE), "speakers"),
    (re.compile(
        r"\b(soundbar|sound bar|home theatre|home theater|subwoofer)"
        , re.IGNORECASE), "soundbars"),

    # Smartwatches & fitness
    (re.compile(
        r"\b(smartwatch|smart watch|apple watch|galaxy watch|amazfit|"
        r"noise colorfit|fire.bolt|garmin|fitbit|samsung watch)"
        , re.IGNORECASE), "smartwatches"),
    (re.compile(
        r"\b(fitness band|fitness tracker|activity tracker)"
        , re.IGNORECASE), "fitness-bands"),

    # Televisions
    (re.compile(
        r"\b(television|smart tv|led tv|oled tv|qled tv|uhd tv|"
        r"4k tv|android tv|google tv|\d{2,3}\s*inch.*tv|\d{2,3}\s*cm.*tv)"
        , re.IGNORECASE), "televisions"),

    # Streaming devices
    (re.compile(
        r"\b(fire tv stick|streaming device|chromecast|roku)"
        , re.IGNORECASE), "streaming-devices"),

    # Projectors
    (re.compile(r"\b(projector)", re.IGNORECASE), "projectors"),

    # Cameras
    (re.compile(
        r"\b(dslr|mirrorless|camera lens|camera)"
        , re.IGNORECASE), "dslr-mirrorless"),
    (re.compile(
        r"\b(action camera|gopro)"
        , re.IGNORECASE), "action-cameras"),

    # Air conditioners
    (re.compile(
        r"\b(air conditioner|split ac|window ac|inverter ac|"
        r"portable ac|ac \d+\.?\d*\s*ton|tower ac|"
        r"\d+\.?\d*\s*ton\s*(split|window|inverter))"
        , re.IGNORECASE), "air-conditioners"),

    # Refrigerators
    (re.compile(
        r"\b(refrigerator|fridge|double door|single door|"
        r"side.by.side|french door fridge|mini fridge)"
        , re.IGNORECASE), "refrigerators"),

    # Washing machines
    (re.compile(
        r"\b(washing machine|washer dryer|front load|top load|"
        r"semi.automatic wash|fully.automatic wash)"
        , re.IGNORECASE), "washing-machines"),

    # Water purifiers
    (re.compile(r"\b(water purifier|ro purifier)", re.IGNORECASE), "water-purifiers"),

    # Air purifiers
    (re.compile(r"\b(air purifier)", re.IGNORECASE), "air-purifiers"),

    # Vacuum cleaners
    (re.compile(r"\b(vacuum cleaner|robot vacuum)", re.IGNORECASE), "vacuum-cleaners"),

    # Fans & coolers
    (re.compile(
        r"\b(ceiling fan|table fan|tower fan|exhaust fan|pedestal fan|"
        r"air cooler|desert cooler)"
        , re.IGNORECASE), "fans-coolers"),

    # Geysers & heaters
    (re.compile(r"\b(geyser|water heater|room heater)", re.IGNORECASE), "geysers-heaters"),

    # Irons
    (re.compile(r"\b(steam iron|garment steamer|\biron\b)", re.IGNORECASE), "irons-steamers"),

    # Kitchen appliances
    (re.compile(
        r"\b(mixer grinder|juicer|blender|food processor|hand blender|"
        r"air fryer|coffee maker|coffee machine|espresso|rice cooker|"
        r"pressure cooker|slow cooker|instant pot|egg boiler|chimney|"
        r"kitchen chimney|dishwasher)"
        , re.IGNORECASE), "kitchen-appliances"),

    # Induction
    (re.compile(r"\b(induction cooktop|induction)", re.IGNORECASE), "induction-cooktops"),

    # Electric kettles
    (re.compile(r"\b(electric kettle)", re.IGNORECASE), "electric-kettles"),

    # Microwave ovens
    (re.compile(r"\b(microwave|otg oven)", re.IGNORECASE), "microwave-ovens"),

    # Sandwich makers
    (re.compile(r"\b(sandwich maker|toaster)", re.IGNORECASE), "sandwich-makers-grills"),

    # Personal care
    (re.compile(
        r"\b(trimmer|electric shaver|beard trimmer|body groomer|nose trimmer)"
        , re.IGNORECASE), "trimmers-shavers"),
    (re.compile(
        r"\b(hair dryer|hair straightener|curling iron)"
        , re.IGNORECASE), "hair-dryers-stylers"),
    (re.compile(r"\b(electric toothbrush)", re.IGNORECASE), "electric-toothbrushes"),

    # Computers peripherals
    (re.compile(
        r"\b(computer monitor|gaming monitor|curved monitor|\bmonitor\b)"
        , re.IGNORECASE), "monitors"),
    (re.compile(r"\b(printer|scanner)", re.IGNORECASE), "printers-scanners"),
    (re.compile(r"\b(router|wifi|mesh router)", re.IGNORECASE), "networking"),
    (re.compile(
        r"\b(keyboard|mechanical keyboard|mouse\b|gaming mouse|mousepad|"
        r"webcam|graphics card|gpu|usb hub|docking station)"
        , re.IGNORECASE), "computer-accessories"),
    (re.compile(
        r"\b(external hard|portable ssd|pen drive|flash drive|"
        r"ssd\s*\d+|nvme|memory card|nas storage)"
        , re.IGNORECASE), "storage-devices"),
    (re.compile(r"\b(desktop|mini pc)", re.IGNORECASE), "desktops"),

    # Gaming
    (re.compile(
        r"\b(ps5|playstation|xbox|nintendo|gaming console)"
        , re.IGNORECASE), "gaming-consoles"),
    (re.compile(
        r"\b(gaming controller|gamepad|joystick|gaming chair|gaming desk)"
        , re.IGNORECASE), "gaming-accessories"),

    # Fitness
    (re.compile(r"\b(treadmill|exercise bike|elliptical)", re.IGNORECASE), "treadmills-cycles"),
    (re.compile(r"\b(dumbbell|weight|gym equipment)", re.IGNORECASE), "dumbbells-weights"),
    (re.compile(r"\b(yoga mat|yoga)", re.IGNORECASE), "yoga-accessories"),

    # Furniture
    (re.compile(r"\b(mattress|bed\b|wardrobe|pillow)", re.IGNORECASE), "bedroom-furniture"),
    (re.compile(r"\b(office chair|study table|desk\b)", re.IGNORECASE), "office-furniture"),
    (re.compile(r"\b(sofa|bean bag|dining table)", re.IGNORECASE), "living-room-furniture"),
    (re.compile(r"\b(shoe rack|bookshelf)", re.IGNORECASE), "storage-furniture"),
    (re.compile(r"\b(bedsheet|curtain|rug\b|carpet)", re.IGNORECASE), "bedsheets"),

    # Bags & luggage
    (re.compile(r"\b(backpack|laptop bag|school bag)", re.IGNORECASE), "backpacks"),
    (re.compile(r"\b(suitcase|trolley bag|luggage)", re.IGNORECASE), "suitcases"),
    (re.compile(r"\b(wallet)", re.IGNORECASE), "wallets"),

    # Books
    (re.compile(r"\b(book|novel|fiction|non.fiction|autobiography)", re.IGNORECASE), "fiction"),

    # Baby
    (re.compile(r"\b(baby stroller|stroller)", re.IGNORECASE), "strollers"),
    (re.compile(r"\b(car seat.*baby|child seat)", re.IGNORECASE), "car-seats"),

    # Automotive
    (re.compile(r"\b(dash cam|car charger|car accessor)", re.IGNORECASE), "car-electronics"),
    (re.compile(r"\b(helmet)", re.IGNORECASE), "helmets"),

    # Musical instruments
    (re.compile(r"\b(guitar)", re.IGNORECASE), "acoustic-guitars"),
    (re.compile(r"\b(piano|keyboard.*piano)", re.IGNORECASE), "digital-pianos"),

    # Health & nutrition
    (re.compile(r"\b(protein|whey)", re.IGNORECASE), "protein-fitness"),
    (re.compile(r"\b(vitamin|supplement)", re.IGNORECASE), "vitamins-minerals"),

    # Beauty
    (re.compile(r"\b(perfume|cologne|fragrance)", re.IGNORECASE), "perfumes"),
    (re.compile(r"\b(deodorant|body spray)", re.IGNORECASE), "deodorants"),

    # Pets
    (re.compile(r"\b(dog food|puppy food)", re.IGNORECASE), "dog-food"),
    (re.compile(r"\b(cat food|kitten food)", re.IGNORECASE), "cat-food"),

    # Plants
    (re.compile(r"\b(indoor plant|artificial plant|money plant)", re.IGNORECASE), "indoor-plants"),
]


class Command(BaseCommand):
    help = "Auto-assign categories to products that have category=NULL based on title keyword matching."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run", action="store_true",
            help="Preview assignments without saving.",
        )
        parser.add_argument(
            "--reindex", action="store_true",
            help="Trigger Meilisearch reindex after assignment.",
        )
        parser.add_argument(
            "--force", action="store_true",
            help="Re-assign categories even for products that already have one.",
        )
        parser.add_argument(
            "--batch-size", type=int, default=500,
            help="Chunk size for iterator (default 500).",
        )

    def handle(self, *args, **options):
        from apps.products.category_mapper import match_by_keywords
        from apps.products.models import Category, Product

        dry_run = options["dry_run"]
        force = options["force"]

        # Load category map (for fallback regex rules + product count update)
        categories = {c.slug: c for c in Category.objects.all()}
        if not categories:
            self.stderr.write(self.style.ERROR(
                "No categories in DB. Run 'python manage.py seed_category_hierarchy' first."
            ))
            return

        # Get products to process
        from django.db.models import Q
        qs = Product.objects.filter(status=Product.Status.ACTIVE)
        if not force:
            # Include products with no category OR with "uncategorized"
            uncat = categories.get("uncategorized")
            if uncat:
                qs = qs.filter(Q(category__isnull=True) | Q(category=uncat))
            else:
                qs = qs.filter(category__isnull=True)

        total = qs.count()
        self.stdout.write(f"Processing {total} products (dry_run={dry_run}, force={force})...")

        assigned = 0
        unmatched = 0
        category_counts: dict[str, int] = {}

        for product in qs.iterator(chunk_size=options["batch_size"]):
            # Step 1: Try canonical keyword mapper (273 keywords, precise)
            cat = match_by_keywords(product.title.lower())

            # Step 2: Fallback to regex rules (broader patterns)
            if not cat:
                matched_slug = self._match_fallback(product.title)
                if matched_slug and matched_slug in categories:
                    cat = categories[matched_slug]

            if cat:
                if not dry_run:
                    product.category = cat
                    product.save(update_fields=["category", "updated_at"])
                assigned += 1
                category_counts[cat.slug] = category_counts.get(cat.slug, 0) + 1
            else:
                unmatched += 1
                if options["verbosity"] >= 2:
                    self.stdout.write(f"  UNMATCHED: {product.title[:80]}")

        # Update category product counts
        if not dry_run:
            for cat_slug, cat in categories.items():
                count = Product.objects.filter(
                    category=cat, status=Product.Status.ACTIVE,
                ).count()
                if cat.product_count != count:
                    cat.product_count = count
                    cat.save(update_fields=["product_count"])

        # Summary
        self.stdout.write(self.style.SUCCESS(
            f"\n{'[DRY RUN] ' if dry_run else ''}Done: {assigned} assigned, "
            f"{unmatched} unmatched out of {total}"
        ))
        for slug, count in sorted(category_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {slug}: {count}")

        # Trigger Meilisearch reindex
        if options["reindex"] and not dry_run and assigned > 0:
            self.stdout.write("Triggering Meilisearch full reindex...")
            try:
                from apps.search.tasks import full_reindex
                full_reindex.delay()
                self.stdout.write(self.style.SUCCESS("Meilisearch reindex queued."))
            except Exception as exc:
                self.stderr.write(self.style.WARNING(f"Meilisearch reindex failed: {exc}"))

    @staticmethod
    def _match_fallback(title: str) -> str | None:
        """Match a product title against fallback regex rules."""
        for pattern, category_slug in _FALLBACK_RULES:
            if pattern.search(title):
                return category_slug
        return None
