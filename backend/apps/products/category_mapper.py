"""Canonical category mapper.

Maps marketplace-specific category paths/breadcrumbs to Whydud's canonical
3-level hierarchy. Uses a 4-step resolution:

  1. Exact mapping lookup (MarketplaceCategoryMapping table)
  2. Keyword-based matching (CANONICAL_KEYWORD_MAP)
  3. Breadcrumb walk (deepest-first matching against known slugs)
  4. Fallback -> "Uncategorized" + create unreviewed MarketplaceCategoryMapping

All products MUST end up in a level=2 subcategory. Never assign to level=0 or level=1.
"""
import logging
import re

from django.utils.text import slugify

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Canonical keyword -> subcategory slug mapping
#
# Consolidated from both amazon_spider.py and flipkart_spider.py
# KEYWORD_CATEGORY_MAP dicts, remapped to canonical level-2 slugs.
# Longer phrases are matched first (multi-word before single-word).
# ---------------------------------------------------------------------------

CANONICAL_KEYWORD_MAP: dict[str, str] = {
    # --- Audio ---
    "headphones": "headphones",
    "headphone": "headphones",
    "over-ear": "headphones",
    "on-ear": "headphones",
    "gaming headsets": "headphones",
    "gaming headset": "headphones",
    "earphones": "earphones-earbuds",
    "earbuds": "earphones-earbuds",
    "earbuds tws": "earphones-earbuds",
    "tws": "earphones-earbuds",
    "true wireless": "earphones-earbuds",
    "neckband": "earphones-earbuds",
    "bluetooth speaker": "speakers",
    "bluetooth speakers": "speakers",
    "portable speaker": "speakers",
    "smart speakers": "speakers",
    "soundbar": "soundbars",
    "soundbars": "soundbars",
    "home theatre": "soundbars",
    "home theatre systems": "soundbars",
    "microphones": "speakers",

    # --- Mobiles & Tablets ---
    "smartphone": "smartphones",
    "smartphones": "smartphones",
    "mobile phone": "smartphones",
    "iphone": "smartphones",
    "galaxy": "smartphones",
    "pixel": "smartphones",
    "phone cases covers": "mobile-accessories",
    "screen protectors": "mobile-accessories",
    "power banks": "mobile-accessories",
    "mobile chargers": "mobile-accessories",
    "mobile holders stands": "mobile-accessories",
    "tablet": "tablets",
    "tablets": "tablets",
    "ipad": "tablets",

    # --- Computers & Peripherals ---
    "laptop": "laptops",
    "laptops": "laptops",
    "notebook": "laptops",
    "macbook": "laptops",
    "gaming laptop": "gaming-laptops",
    "gaming laptops": "gaming-laptops",
    "gaming monitors": "monitors",
    "monitor": "monitors",
    "monitors": "monitors",
    "printer": "printers-scanners",
    "printers": "printers-scanners",
    "scanner": "printers-scanners",
    "routers": "networking",
    "router": "networking",
    "wifi mesh systems": "networking",
    "computer keyboards": "computer-accessories",
    "computer mouse": "computer-accessories",
    "webcams": "computer-accessories",
    "external hard drives": "storage-devices",
    "pen drives": "storage-devices",
    "graphics cards": "computer-accessories",
    "ssd internal": "storage-devices",
    "memory cards": "storage-devices",
    "nas storage": "storage-devices",
    "desktops": "desktops",
    "desktop": "desktops",

    # --- TVs & Entertainment ---
    "televisions": "televisions",
    "television": "televisions",
    "tv": "televisions",
    "smart tv": "televisions",
    "tv wall mounts": "televisions",
    "projectors": "projectors",
    "projector": "projectors",
    "streaming devices": "streaming-devices",
    "fire stick": "streaming-devices",
    "chromecast": "streaming-devices",

    # --- Cameras & Photography ---
    "cameras": "dslr-mirrorless",
    "camera": "dslr-mirrorless",
    "dslr": "dslr-mirrorless",
    "mirrorless": "dslr-mirrorless",
    "camera lenses": "camera-accessories",
    "camera tripods": "camera-accessories",
    "action cameras": "action-cameras",
    "action camera": "action-cameras",
    "gopro": "action-cameras",
    "drones cameras": "camera-accessories",
    "security cameras": "camera-accessories",
    "baby monitors": "camera-accessories",
    "dash cameras": "car-electronics",

    # --- Wearables ---
    "smartwatches": "smartwatches",
    "smartwatch": "smartwatches",
    "apple watch": "smartwatches",
    "fitness bands": "fitness-bands",
    "fitness band": "fitness-bands",
    "fitness tracker": "fitness-bands",

    # --- Gaming ---
    "gaming consoles": "gaming-consoles",
    "gaming console": "gaming-consoles",
    "playstation": "gaming-consoles",
    "xbox": "gaming-consoles",
    "nintendo": "gaming-consoles",
    "gaming controllers": "gaming-accessories",
    "gaming chairs": "gaming-accessories",
    "gaming accessories": "gaming-accessories",
    "video games": "video-games",

    # --- Home Appliances ---
    "air conditioner": "air-conditioners",
    "air conditioners": "air-conditioners",
    "split ac": "air-conditioners",
    "window ac": "air-conditioners",
    "refrigerator": "refrigerators",
    "refrigerators": "refrigerators",
    "fridge": "refrigerators",
    "washing machine": "washing-machines",
    "washing machines": "washing-machines",
    "water purifier": "water-purifiers",
    "water purifiers": "water-purifiers",
    "air purifier": "air-purifiers",
    "air purifiers": "air-purifiers",
    "car air purifiers": "air-purifiers",
    "vacuum cleaner": "vacuum-cleaners",
    "vacuum cleaners": "vacuum-cleaners",
    "robot vacuum cleaners": "vacuum-cleaners",
    "fans": "fans-coolers",
    "fan": "fans-coolers",
    "cooler": "fans-coolers",
    "room heaters": "geysers-heaters",
    "water heaters geysers": "geysers-heaters",
    "geyser": "geysers-heaters",
    "irons steamers": "irons-steamers",
    "iron": "irons-steamers",
    "dishwashers": "kitchen-appliances",
    "chimneys": "kitchen-appliances",

    # --- Kitchen ---
    "cookware sets": "cookware",
    "cookware": "cookware",
    "pressure cookers": "cookware",
    "mixer grinders": "mixer-grinders",
    "mixer grinder": "mixer-grinders",
    "juicer mixer grinder": "mixer-grinders",
    "hand blenders": "mixer-grinders",
    "induction cooktops": "induction-cooktops",
    "induction cooktop": "induction-cooktops",
    "electric kettles": "electric-kettles",
    "electric kettle": "electric-kettles",
    "air fryers": "kitchen-appliances",
    "air fryer": "kitchen-appliances",
    "coffee machines": "kitchen-appliances",
    "microwave ovens": "microwave-ovens",
    "microwave oven": "microwave-ovens",
    "sandwich makers": "sandwich-makers-grills",
    "toasters": "sandwich-makers-grills",
    "rice cookers": "kitchen-appliances",
    "water bottles": "kitchen-storage",
    "lunch boxes": "kitchen-storage",
    "kitchen storage": "kitchen-storage",

    # --- Personal Care Appliances ---
    "trimmers": "trimmers-shavers",
    "trimmer": "trimmers-shavers",
    "electric shavers": "trimmers-shavers",
    "electric shaver": "trimmers-shavers",
    "hair dryers": "hair-dryers-stylers",
    "hair dryer": "hair-dryers-stylers",
    "hair straighteners": "hair-dryers-stylers",
    "hair straightener": "hair-dryers-stylers",
    "electric toothbrushes": "electric-toothbrushes",
    "electric toothbrush": "electric-toothbrushes",
    "epilators": "trimmers-shavers",

    # --- Furniture ---
    "mattresses": "bedroom-furniture",
    "mattress": "bedroom-furniture",
    "beds": "bedroom-furniture",
    "bed": "bedroom-furniture",
    "wardrobes": "bedroom-furniture",
    "wardrobe": "bedroom-furniture",
    "office chairs": "office-furniture",
    "office chair": "office-furniture",
    "study tables": "office-furniture",
    "study table": "office-furniture",
    "sofas": "living-room-furniture",
    "sofa": "living-room-furniture",
    "bean bags": "living-room-furniture",
    "dining tables": "living-room-furniture",
    "shoe racks": "storage-furniture",
    "curtains": "bedsheets",
    "bedsheets": "bedsheets",

    # --- Garden & Outdoor ---
    "indoor plant": "indoor-plants",
    "indoor plants": "indoor-plants",
    "artificial plant": "indoor-plants",
    "money plant": "indoor-plants",
    "succulent": "indoor-plants",

    # --- Smart Home ---
    "smart plugs": "computer-accessories",
    "smart bulbs": "lighting",
    "smart door locks": "computer-accessories",
    "video doorbells": "camera-accessories",

    # --- Fitness & Sports ---
    "treadmills": "treadmills-cycles",
    "treadmill": "treadmills-cycles",
    "exercise bikes": "treadmills-cycles",
    "exercise bike": "treadmills-cycles",
    "dumbbells weights": "dumbbells-weights",
    "dumbbells": "dumbbells-weights",
    "dumbbell": "dumbbells-weights",
    "yoga mats": "yoga-accessories",
    "yoga mat": "yoga-accessories",
    "gym equipment": "dumbbells-weights",
    "cricket": "cricket",
    "badminton": "badminton",
    "football": "football",

    # --- Fashion ---
    "sunglasses": "mens-accessories",
    "watches men": "mens-watches",
    "watches women": "womens-watches",
    "handbags": "womens-handbags",

    # --- Bags & Luggage ---
    "laptop bags backpacks": "backpacks",
    "backpack": "backpacks",
    "suitcases trolley": "suitcases",
    "suitcase": "suitcases",
    "wallets": "wallets",
    "wallet": "wallets",

    # --- Books & Stationery ---
    "books bestsellers": "fiction",
    "books": "fiction",
    "school bags": "backpacks",

    # --- Baby & Kids ---
    "baby strollers": "strollers",
    "stroller": "strollers",
    "car seats baby": "car-seats",
    "baby toys": "educational-toys",

    # --- Automotive ---
    "car chargers": "car-electronics",
    "car accessories": "car-electronics",
    "tyre inflators": "car-electronics",
    "helmet": "helmets",
    "helmets": "helmets",

    # --- Musical Instruments ---
    "guitars": "acoustic-guitars",
    "guitar": "acoustic-guitars",
    "keyboards pianos": "keyboards-music",
    "keyboard piano": "keyboards-music",
    "piano": "digital-pianos",

    # --- Health ---
    "protein": "protein-fitness",
    "whey protein": "protein-fitness",
    "vitamins": "vitamins-minerals",
    "supplement": "vitamins-minerals",

    # --- Beauty ---
    "perfume": "perfumes",
    "perfumes": "perfumes",
    "deodorant": "deodorants",
    "deodorants": "deodorants",

    # --- Pet Supplies ---
    "dog food": "dog-food",
    "cat food": "cat-food",
}

# Pre-sort keywords by length (longest first) for greedy matching
_SORTED_KEYWORDS = sorted(CANONICAL_KEYWORD_MAP.keys(), key=len, reverse=True)


def resolve_canonical_category(
    marketplace_slug: str,
    breadcrumbs: list[str] | None,
    title: str,
    raw_category: str | None = None,
):
    """Resolve a scraped product to its canonical Whydud subcategory (level=2).

    Args:
        marketplace_slug: e.g. "amazon-in", "flipkart"
        breadcrumbs: e.g. ["Electronics", "Headphones, Earbuds & Accessories", "Headphones"]
        title: product title for keyword extraction
        raw_category: optional marketplace category string from JSON-LD

    Returns:
        Category instance (always level=2), or None if resolution fails entirely.
    """
    from apps.products.models import Category, Marketplace, MarketplaceCategoryMapping

    # Build breadcrumb path string
    breadcrumb_path = " > ".join(breadcrumbs) if breadcrumbs else ""
    leaf_slug = slugify(breadcrumbs[-1]) if breadcrumbs else ""

    # ---- Step 1: Exact mapping lookup ----
    if leaf_slug and marketplace_slug:
        try:
            marketplace = Marketplace.objects.filter(slug=marketplace_slug).first()
            if marketplace:
                mapping = MarketplaceCategoryMapping.objects.filter(
                    marketplace=marketplace,
                    marketplace_category_slug=leaf_slug,
                ).select_related("canonical_category").first()
                if mapping and mapping.canonical_category.level == 2:
                    return mapping.canonical_category
        except Exception:
            logger.debug("Step 1 lookup failed for %s/%s", marketplace_slug, leaf_slug)

    # ---- Step 2: Keyword-based matching ----
    search_text = f"{breadcrumb_path} {title} {raw_category or ''}".lower()
    category = _match_by_keywords(search_text)
    if category:
        _auto_create_mapping(marketplace_slug, breadcrumb_path, leaf_slug, category)
        return category

    # ---- Step 3: Breadcrumb walk ----
    if breadcrumbs:
        category = _match_by_breadcrumb_walk(breadcrumbs)
        if category:
            _auto_create_mapping(marketplace_slug, breadcrumb_path, leaf_slug, category)
            return category

    # ---- Step 4: Fallback ----
    uncategorized = _get_or_create_uncategorized()
    if leaf_slug and marketplace_slug:
        _auto_create_mapping(
            marketplace_slug, breadcrumb_path, leaf_slug, uncategorized,
            confidence="unreviewed",
        )
    logger.warning(
        "Unmapped category: %s | %s | %s",
        marketplace_slug, breadcrumbs, title[:80],
    )
    return uncategorized


def _match_by_keywords(search_text: str):
    """Match text against CANONICAL_KEYWORD_MAP (longest phrase first)."""
    from apps.products.models import Category

    for keyword in _SORTED_KEYWORDS:
        if keyword in search_text:
            target_slug = CANONICAL_KEYWORD_MAP[keyword]
            cat = Category.objects.filter(slug=target_slug, level=2).first()
            if cat:
                return cat
    return None


def _match_by_breadcrumb_walk(breadcrumbs: list[str]):
    """Walk breadcrumbs deepest to shallowest, match slugified segments."""
    from apps.products.models import Category

    for crumb in reversed(breadcrumbs):
        clean = crumb.strip()
        if not clean or clean.lower() in {"home", "all categories", "all", "search", "products"}:
            continue
        slug = slugify(clean)
        if not slug or len(slug) < 2:
            continue
        cat = Category.objects.filter(slug=slug, level=2).first()
        if cat:
            return cat
    return None


def _auto_create_mapping(
    marketplace_slug: str,
    breadcrumb_path: str,
    leaf_slug: str,
    category,
    confidence: str = "auto",
):
    """Auto-create a MarketplaceCategoryMapping for fast future lookups."""
    if not leaf_slug or not marketplace_slug:
        return
    from apps.products.models import Marketplace, MarketplaceCategoryMapping

    try:
        marketplace = Marketplace.objects.filter(slug=marketplace_slug).first()
        if not marketplace:
            return
        MarketplaceCategoryMapping.objects.update_or_create(
            marketplace=marketplace,
            marketplace_category_slug=leaf_slug,
            defaults={
                "marketplace_category_path": breadcrumb_path[:1000],
                "canonical_category": category,
                "confidence": confidence,
            },
        )
    except Exception:
        logger.debug("Failed to auto-create mapping for %s/%s", marketplace_slug, leaf_slug, exc_info=True)


def _get_or_create_uncategorized():
    """Return the 'Uncategorized' subcategory, creating if needed."""
    from apps.products.models import Category

    # Check if it exists
    uncat = Category.objects.filter(slug="uncategorized", level=2).first()
    if uncat:
        return uncat

    # Create "Other" department -> "Other" category -> "Uncategorized" subcategory
    other_dept, _ = Category.objects.get_or_create(
        slug="other",
        defaults={
            "name": "Other",
            "level": 0,
            "is_active": False,
            "display_order": 999,
        },
    )
    other_cat, _ = Category.objects.get_or_create(
        slug="other-general",
        defaults={
            "name": "General",
            "level": 1,
            "parent": other_dept,
            "is_active": False,
            "display_order": 0,
        },
    )
    uncat, _ = Category.objects.get_or_create(
        slug="uncategorized",
        defaults={
            "name": "Uncategorized",
            "level": 2,
            "parent": other_cat,
            "is_active": False,
            "display_order": 0,
        },
    )
    return uncat
