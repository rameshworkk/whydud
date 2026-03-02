"""Management command to auto-assign categories to products missing them.

Uses keyword matching on product titles to map to the correct category.
Run after scraping to backfill products that were ingested without category info.

Usage:
    python manage.py assign_categories          # assign + print summary
    python manage.py assign_categories --dry-run # preview without saving
    python manage.py assign_categories --reindex # also trigger Meilisearch reindex
"""
import re
from django.core.management.base import BaseCommand

# ---------------------------------------------------------------------------
# Keyword → category slug mapping
#
# Order matters: more specific patterns are checked first.
# Each tuple: (compiled_regex, category_slug)
# ---------------------------------------------------------------------------

_CATEGORY_RULES: list[tuple[re.Pattern, str]] = [
    # ── Smartphones & Accessories ──────────────────────────────────────
    (re.compile(
        r"\b(smartphone|mobile phone|iphone|galaxy [sazm]\d|redmi|realme \d|"
        r"oneplus \d|poco|pixel \d|vivo [tvyx]|oppo [afr]|iqoo|moto [gex]|"
        r"nothing phone|samsung galaxy [sazm]|nokia \d)"
        , re.IGNORECASE), "smartphones"),
    (re.compile(
        r"\b(phone case|phone cover|back cover|screen protector|tempered glass|"
        r"mobile charger|charging cable|usb[-\s]c cable|lightning cable|"
        r"car charger|wireless charger|phone holder|phone stand|sim card|"
        r"otg adapter|phone grip|pop socket)"
        , re.IGNORECASE), "smartphones"),
    (re.compile(
        r"\b(power bank|portable charger|battery pack)"
        , re.IGNORECASE), "smartphones"),

    # ── Laptops ────────────────────────────────────────────────────────
    (re.compile(
        r"\b(laptop|notebook|macbook|chromebook|thinkpad|ideapad|vivobook|"
        r"zenbook|inspiron|pavilion|probook|elitebook|surface pro|surface laptop|"
        r"gaming laptop|ultrabook)"
        , re.IGNORECASE), "laptops"),

    # ── Tablets ────────────────────────────────────────────────────────
    (re.compile(
        r"\b(tablet|ipad|galaxy tab|fire\s*hd|kindle fire|lenovo tab|"
        r"realme pad|oneplus pad|xiaomi pad|stylus pen|tablet cover|tablet case)"
        , re.IGNORECASE), "tablets"),

    # ── Audio ──────────────────────────────────────────────────────────
    (re.compile(
        r"\b(headphone|earphone|earbud|earbuds|tws|neckband|headset|"
        r"bluetooth speaker|portable speaker|soundbar|sound bar|"
        r"home theatre|home theater|subwoofer|wired earphone|"
        r"over.ear|on.ear|in.ear|true wireless|anc headphone|"
        r"noise cancell|party speaker|microphone|karaoke|"
        r"jbl|boat |boats |boAt |sony wh-|sony wf-|sennheiser|"
        r"audio.technica|marshall speaker|bose |harman)"
        , re.IGNORECASE), "audio"),

    # ── Smartwatches & Fitness ─────────────────────────────────────────
    (re.compile(
        r"\b(smartwatch|smart watch|fitness band|fitness tracker|"
        r"apple watch|galaxy watch|amazfit|noise colorfit|fire.bolt|"
        r"garmin|fitbit|samsung watch|activity tracker)"
        , re.IGNORECASE), "smartwatches"),

    # ── Televisions ────────────────────────────────────────────────────
    (re.compile(
        r"\b(television|smart tv|led tv|oled tv|qled tv|uhd tv|"
        r"4k tv|android tv|google tv|fire tv stick|streaming device|"
        r"chromecast|roku|projector|tv wall mount|tv stand|"
        r"\d{2,3}\s*inch.*tv|\d{2,3}\s*cm.*tv)"
        , re.IGNORECASE), "televisions"),

    # ── Cameras ────────────────────────────────────────────────────────
    (re.compile(
        r"\b(camera|dslr|mirrorless|action camera|gopro|webcam|"
        r"camera lens|tripod|gimbal|ring light|sd card.*camera|"
        r"instant camera|polaroid|cctv|security camera|ip camera|"
        r"baby monitor|video doorbell|dash cam)"
        , re.IGNORECASE), "cameras"),

    # ── Air Conditioners ───────────────────────────────────────────────
    (re.compile(
        r"\b(air conditioner|split ac|window ac|inverter ac|"
        r"portable ac|ac \d+\.?\d*\s*ton|tower ac|"
        r"\d+\.?\d*\s*ton\s*(split|window|inverter))"
        , re.IGNORECASE), "air-conditioners"),

    # ── Refrigerators ──────────────────────────────────────────────────
    (re.compile(
        r"\b(refrigerator|fridge|double door|single door|"
        r"side.by.side|french door fridge|mini fridge|"
        r"\d+\s*litr?e?\s*(refrigerator|fridge|double|single))"
        , re.IGNORECASE), "refrigerators"),

    # ── Washing Machines ───────────────────────────────────────────────
    (re.compile(
        r"\b(washing machine|washer dryer|front load|top load|"
        r"semi.automatic wash|fully.automatic wash|"
        r"\d+\.?\d*\s*kg\s*(washing|front|top|semi|fully))"
        , re.IGNORECASE), "washing-machines"),

    # ── Appliances (general — after specific sub-categories) ───────────
    (re.compile(
        r"\b(air purifier|water purifier|vacuum cleaner|robot vacuum|"
        r"geyser|water heater|chimney|kitchen chimney|"
        r"microwave|oven|otg oven|dishwasher|room heater|"
        r"dehumidifier|humidifier|fan\s|ceiling fan|table fan|tower fan|"
        r"exhaust fan|pedestal fan|cooler|air cooler|desert cooler)"
        , re.IGNORECASE), "appliances"),

    # ── Kitchen Tools ──────────────────────────────────────────────────
    (re.compile(
        r"\b(mixer grinder|juicer|blender|food processor|hand blender|"
        r"induction cooktop|electric kettle|air fryer|coffee maker|"
        r"coffee machine|espresso|toaster|sandwich maker|roti maker|"
        r"rice cooker|pressure cooker|slow cooker|instant pot|"
        r"iron |steam iron|garment steamer|hand mixer|egg boiler|"
        r"choppers?|vegetable|slicer|peeler)"
        , re.IGNORECASE), "kitchen-tools"),

    # ── Computers peripherals → laptops (closest match) ────────────────
    (re.compile(
        r"\b(monitor\b|computer monitor|gaming monitor|curved monitor|"
        r"keyboard|mechanical keyboard|wireless keyboard|mouse\b|"
        r"gaming mouse|wireless mouse|mousepad|laptop bag|laptop stand|"
        r"laptop sleeve|docking station|usb hub|kvm switch|"
        r"external hard|portable ssd|pen drive|flash drive|"
        r"graphics card|gpu|ram\s*\d+\s*gb|ssd\s*\d+|nvme|"
        r"router|wifi|mesh router|range extender|ethernet|"
        r"ups |uninterruptible|surge protector|printer|scanner)"
        , re.IGNORECASE), "laptops"),

    # ── Gaming → laptops (no separate gaming category) ─────────────────
    (re.compile(
        r"\b(gaming chair|gaming controller|gamepad|joystick|"
        r"gaming headset|gaming desk|ps5|playstation|xbox|nintendo)"
        , re.IGNORECASE), "laptops"),

    # ── Personal care / grooming / beauty → closest: kitchen-tools or appliances
    (re.compile(
        r"\b(trimmer|electric shaver|hair dryer|hair straightener|"
        r"curling iron|epilator|electric toothbrush|massager|"
        r"body groomer|nose trimmer|beard trimmer)"
        , re.IGNORECASE), "appliances"),

    # ── Fitness / sports equipment ─────────────────────────────────────
    (re.compile(
        r"\b(treadmill|exercise bike|elliptical|dumbbell|weight|"
        r"yoga mat|resistance band|pull.up bar|gym|bench press|"
        r"cycling|skipping rope|boxing glove)"
        , re.IGNORECASE), "appliances"),

    # ── Home & furniture → home-kitchen ────────────────────────────────
    (re.compile(
        r"\b(mattress|office chair|study table|bed\b|sofa|"
        r"shoe rack|bookshelf|wardrobe|desk\b|pillow|"
        r"bedsheet|curtain|rug\b|carpet|bean bag)"
        , re.IGNORECASE), "home-kitchen"),

    # ── Smart home → electronics ───────────────────────────────────────
    (re.compile(
        r"\b(smart plug|smart bulb|smart light|smart lock|"
        r"smart door|alexa|echo dot|google home|google nest|"
        r"smart display|smart speaker)"
        , re.IGNORECASE), "electronics"),

    # ── Baby / kids ────────────────────────────────────────────────────
    (re.compile(
        r"\b(baby stroller|car seat.*baby|baby monitor|high chair|"
        r"diaper|baby bottle|sterilizer)"
        , re.IGNORECASE), "home-kitchen"),

    # ── Car accessories → electronics ──────────────────────────────────
    (re.compile(
        r"\b(dash cam|car charger|car air purifier|tyre inflator|"
        r"car vacuum|car mount|gps tracker|car stereo)"
        , re.IGNORECASE), "electronics"),

    # ── Musical instruments → electronics ──────────────────────────────
    (re.compile(
        r"\b(guitar|keyboard.*piano|digital piano|ukulele|"
        r"cajon|drum pad|synthesizer)"
        , re.IGNORECASE), "electronics"),

    # ── Luggage / bags → fashion ───────────────────────────────────────
    (re.compile(
        r"\b(laptop bag|backpack|suitcase|trolley bag|duffle|"
        r"messenger bag|briefcase|travel bag|luggage)"
        , re.IGNORECASE), "fashion"),
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

    def handle(self, *args, **options):
        from apps.products.models import Category, Product

        dry_run = options["dry_run"]
        force = options["force"]

        # Load category map
        categories = {c.slug: c for c in Category.objects.all()}
        if not categories:
            self.stderr.write(self.style.ERROR(
                "No categories in DB. Run 'python manage.py seed_data' first."
            ))
            return

        # Get products to process
        qs = Product.objects.filter(status=Product.Status.ACTIVE)
        if not force:
            qs = qs.filter(category__isnull=True)

        total = qs.count()
        self.stdout.write(f"Processing {total} products (dry_run={dry_run}, force={force})...")

        assigned = 0
        unmatched = 0
        category_counts: dict[str, int] = {}

        for product in qs.iterator(chunk_size=500):
            matched_slug = self._match_category(product.title)
            if matched_slug and matched_slug in categories:
                if not dry_run:
                    product.category = categories[matched_slug]
                    product.save(update_fields=["category", "updated_at"])
                assigned += 1
                category_counts[matched_slug] = category_counts.get(matched_slug, 0) + 1
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
            f"\n{'[DRY RUN] ' if dry_run else ''}Done: {assigned} assigned, {unmatched} unmatched out of {total}"
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
    def _match_category(title: str) -> str | None:
        """Match a product title against category rules. Returns category slug or None."""
        for pattern, category_slug in _CATEGORY_RULES:
            if pattern.search(title):
                return category_slug
        return None
