"""
Seed production-grade data for Whydud.

Usage:
    python manage.py seed_data
    python manage.py seed_data --flush   # Wipe and re-seed
"""

import random
import uuid
from datetime import date, datetime, timedelta
from decimal import Decimal

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone

from apps.accounts.models import PaymentMethod, User, WhydudEmail
from apps.deals.models import Deal
from apps.discussions.models import DiscussionReply, DiscussionThread
from apps.email_intel.models import (
    DetectedSubscription,
    InboxEmail,
    ParsedOrder,
    RefundTracking,
    ReturnWindow,
)
from apps.pricing.models import MarketplaceOffer, PriceSnapshot
from apps.products.models import (
    BankCard,
    Brand,
    Category,
    Marketplace,
    Product,
    ProductListing,
    Seller,
)
from apps.reviews.models import Review
from apps.rewards.models import (
    GiftCardCatalog,
    RewardBalance,
    RewardPointsLedger,
)
from apps.scoring.models import DudScoreConfig, DudScoreHistory
from apps.tco.models import CityReferenceData, TCOModel
from apps.wishlists.models import Wishlist, WishlistItem


def _paisa(rupees: int | float) -> Decimal:
    """Convert rupees to paisa as Decimal(12,2)."""
    return Decimal(str(int(rupees * 100))) + Decimal("0.00")


def _rand_paisa(low: int, high: int) -> Decimal:
    """Random price in paisa between low/high rupees."""
    return _paisa(random.randint(low, high))


def _dt(days_ago: int = 0) -> datetime:
    return timezone.now() - timedelta(days=days_ago)


class Command(BaseCommand):
    help = "Seed Whydud database with production-grade sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing data before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            self._flush()

        self.stdout.write("Seeding data...")

        marketplaces = self._seed_marketplaces()
        categories = self._seed_categories()
        brands = self._seed_brands()
        products = self._seed_products(categories, brands)
        sellers = self._seed_sellers(marketplaces)
        listings = self._seed_listings(products, marketplaces, sellers)
        self._seed_price_snapshots(listings, products, marketplaces)
        self._seed_reviews(listings, products)
        self._update_product_stats(products)
        self._seed_bank_cards()
        self._seed_marketplace_offers(marketplaces, categories)
        self._seed_deals(products, listings, marketplaces)
        self._seed_dudscore_config()
        self._seed_dudscore_history(products)
        self._seed_discussions(products)
        self._seed_cities()
        self._seed_tco_models(categories)
        self._seed_gift_card_catalog()

        # User-specific data
        user = self._seed_test_user()
        self._seed_wishlists(user, products)
        self._seed_rewards(user)
        self._seed_inbox(user, products)

        self.stdout.write(self.style.SUCCESS("Seed data created successfully!"))

    def _flush(self):
        """Delete seeded data (preserving migrations, marketplaces)."""
        models_to_flush = [
            WishlistItem, Wishlist, RewardPointsLedger, RewardBalance,
            GiftCardCatalog, DetectedSubscription, ReturnWindow,
            RefundTracking, ParsedOrder, InboxEmail, DiscussionReply,
            DiscussionThread, Deal, Review,
            MarketplaceOffer, ProductListing, Seller, Product,
            BankCard, Brand, Category, DudScoreConfig, CityReferenceData,
            TCOModel,
        ]
        for m in models_to_flush:
            if m is not None:
                m.objects.all().delete()
        # Flush TimescaleDB tables via raw SQL
        with connection.cursor() as c:
            c.execute("DELETE FROM price_snapshots")
            c.execute('DELETE FROM "scoring"."dudscore_history"')
        User.objects.filter(email="test@whydud.com").delete()

    # ── Marketplaces ──────────────────────────────────────────────

    def _seed_marketplaces(self):
        """Get existing marketplaces (seeded by migration 0002)."""
        mp = {m.slug: m for m in Marketplace.objects.all()}
        self.stdout.write(f"  Marketplaces: {len(mp)} existing")
        return mp

    # ── Categories ────────────────────────────────────────────────

    def _seed_categories(self):
        DATA = [
            # Top-level
            ("electronics", "Electronics", None, 0, False),
            ("fashion", "Fashion", None, 0, False),
            ("home-kitchen", "Home & Kitchen", None, 0, False),
            # Level 1 under Electronics
            ("smartphones", "Smartphones", "electronics", 1, False),
            ("laptops", "Laptops", "electronics", 1, False),
            ("audio", "Audio", "electronics", 1, False),
            ("smartwatches", "Smartwatches", "electronics", 1, False),
            ("televisions", "Televisions", "electronics", 1, False),
            ("cameras", "Cameras", "electronics", 1, False),
            ("tablets", "Tablets", "electronics", 1, False),
            # Level 1 under Home & Kitchen
            ("appliances", "Appliances", "home-kitchen", 1, True),
            ("kitchen-tools", "Kitchen Tools", "home-kitchen", 1, False),
            # Level 2 under Appliances
            ("air-conditioners", "Air Conditioners", "appliances", 2, True),
            ("refrigerators", "Refrigerators", "appliances", 2, True),
            ("washing-machines", "Washing Machines", "appliances", 2, True),
        ]
        cats = {}
        for slug, name, parent_slug, level, has_tco in DATA:
            parent = cats.get(parent_slug)
            obj, _ = Category.objects.update_or_create(
                slug=slug,
                defaults=dict(name=name, parent=parent, level=level, has_tco_model=has_tco),
            )
            cats[slug] = obj
        self.stdout.write(f"  Categories: {len(cats)}")
        return cats

    # ── Brands ────────────────────────────────────────────────────

    def _seed_brands(self):
        DATA = [
            ("samsung", "Samsung", ["Samsung India"], True),
            ("apple", "Apple", ["Apple India"], True),
            ("oneplus", "OnePlus", ["1+", "One Plus"], True),
            ("xiaomi", "Xiaomi", ["Mi", "Redmi", "POCO"], True),
            ("boat", "boAt", ["boat", "Boat"], True),
            ("noise", "Noise", ["Noise India", "NoiseFit"], True),
            ("sony", "Sony", ["Sony India"], True),
            ("lg", "LG", ["LG Electronics"], True),
            ("prestige", "Prestige", ["TTK Prestige"], True),
            ("dyson", "Dyson", [], True),
            ("jbl", "JBL", ["JBL India", "Harman"], True),
            ("realme", "Realme", ["realme"], True),
            ("hp", "HP", ["Hewlett-Packard", "HP India"], True),
            ("dell", "Dell", ["Dell Technologies"], True),
            ("lenovo", "Lenovo", ["Lenovo India"], True),
            ("asus", "ASUS", ["Asus India"], True),
            ("whirlpool", "Whirlpool", ["Whirlpool India"], True),
            ("daikin", "Daikin", ["Daikin India"], True),
            ("voltas", "Voltas", ["Voltas Beko"], True),
            ("bajaj", "Bajaj", ["Bajaj Electricals"], True),
            ("philips", "Philips", ["Philips India"], True),
            ("bose", "Bose", [], True),
            ("nothing", "Nothing", ["Nothing Phone"], True),
            ("google", "Google", ["Google Pixel"], True),
            ("motorola", "Motorola", ["Moto"], True),
            ("oppo", "OPPO", [], True),
            ("vivo", "vivo", ["Vivo India"], True),
            ("sennheiser", "Sennheiser", [], True),
            ("havells", "Havells", ["Havells India"], True),
            ("crompton", "Crompton", ["Crompton Greaves"], True),
        ]
        brands = {}
        for slug, name, aliases, verified in DATA:
            obj, _ = Brand.objects.update_or_create(
                slug=slug,
                defaults=dict(
                    name=name,
                    aliases=aliases,
                    verified=verified,
                    logo_url=f"https://placehold.co/120x40/eee/333?text={name}",
                ),
            )
            brands[slug] = obj
        self.stdout.write(f"  Brands: {len(brands)}")
        return brands

    # ── Products ──────────────────────────────────────────────────

    def _seed_products(self, cats, brands):
        PRODUCTS = [
            # Smartphones
            {
                "slug": "samsung-galaxy-s24-fe",
                "title": "Samsung Galaxy S24 FE 5G (8GB RAM, 128GB)",
                "brand": "samsung",
                "category": "smartphones",
                "description": "The Galaxy S24 FE brings flagship Galaxy AI features to more users. Powered by the Exynos 2400e processor with a brilliant 6.7-inch Dynamic AMOLED 2X display, 50MP triple camera with Nightography, and a 4700mAh battery.",
                "specs": {
                    "Display": "6.7\" Dynamic AMOLED 2X, 120Hz",
                    "Processor": "Exynos 2400e",
                    "RAM": "8 GB",
                    "Storage": "128 GB",
                    "Rear Camera": "50MP + 12MP + 8MP",
                    "Front Camera": "10MP",
                    "Battery": "4700 mAh",
                    "OS": "Android 14, One UI 6.1",
                    "5G": "Yes",
                    "Weight": "213 g",
                },
                "prices": {"amazon_in": 29999, "flipkart": 30999, "croma": 32999},
                "mrps": {"amazon_in": 65999, "flipkart": 65999, "croma": 65999},
            },
            {
                "slug": "oneplus-13r",
                "title": "OnePlus 13R 5G (12GB RAM, 256GB)",
                "brand": "oneplus",
                "category": "smartphones",
                "description": "OnePlus 13R features the Snapdragon 8 Gen 3 chipset, a 6.78-inch ProXDR AMOLED display with 120Hz refresh rate, 50MP Sony LYT-700 triple camera, 6000mAh battery with 80W SUPERVOOC charging.",
                "specs": {
                    "Display": "6.78\" ProXDR AMOLED, 120Hz",
                    "Processor": "Snapdragon 8 Gen 3",
                    "RAM": "12 GB",
                    "Storage": "256 GB",
                    "Rear Camera": "50MP + 8MP + 50MP",
                    "Front Camera": "16MP",
                    "Battery": "6000 mAh",
                    "OS": "Android 15, OxygenOS 15",
                    "5G": "Yes",
                    "Weight": "206 g",
                },
                "prices": {"amazon_in": 42999, "flipkart": 42999},
                "mrps": {"amazon_in": 44999, "flipkart": 44999},
            },
            {
                "slug": "iphone-16",
                "title": "Apple iPhone 16 (128GB)",
                "brand": "apple",
                "category": "smartphones",
                "description": "iPhone 16 features the A18 chip with Apple Intelligence, a 48MP Fusion camera with 2x Telephoto, Action button, USB-C, and all-day battery life.",
                "specs": {
                    "Display": "6.1\" Super Retina XDR OLED",
                    "Processor": "A18 Bionic",
                    "RAM": "8 GB",
                    "Storage": "128 GB",
                    "Rear Camera": "48MP + 12MP",
                    "Front Camera": "12MP TrueDepth",
                    "Battery": "3561 mAh",
                    "OS": "iOS 18",
                    "5G": "Yes",
                    "Weight": "170 g",
                },
                "prices": {"amazon_in": 71999, "flipkart": 71999, "croma": 74999},
                "mrps": {"amazon_in": 79900, "flipkart": 79900, "croma": 79900},
            },
            {
                "slug": "redmi-note-13-pro-plus",
                "title": "Redmi Note 13 Pro+ 5G (8GB RAM, 256GB)",
                "brand": "xiaomi",
                "category": "smartphones",
                "description": "Redmi Note 13 Pro+ 5G with 200MP OIS camera, 120W HyperCharge, Dimensity 7200-Ultra, 6.67\" 1.5K curved AMOLED display with 120Hz.",
                "specs": {
                    "Display": "6.67\" 1.5K Curved AMOLED, 120Hz",
                    "Processor": "Dimensity 7200-Ultra",
                    "RAM": "8 GB",
                    "Storage": "256 GB",
                    "Rear Camera": "200MP + 8MP + 2MP",
                    "Front Camera": "16MP",
                    "Battery": "5000 mAh",
                    "OS": "Android 14, MIUI 15",
                    "5G": "Yes",
                    "Weight": "204 g",
                },
                "prices": {"amazon_in": 26999, "flipkart": 25999},
                "mrps": {"amazon_in": 32999, "flipkart": 32999},
            },
            {
                "slug": "nothing-phone-2a",
                "title": "Nothing Phone (2a) 5G (8GB RAM, 128GB)",
                "brand": "nothing",
                "category": "smartphones",
                "description": "Nothing Phone (2a) with unique Glyph Interface, Dimensity 7200 Pro, 6.7\" flexible AMOLED 120Hz, 50MP dual camera, 5000mAh battery with 45W fast charging.",
                "specs": {
                    "Display": "6.7\" Flexible AMOLED, 120Hz",
                    "Processor": "Dimensity 7200 Pro",
                    "RAM": "8 GB",
                    "Storage": "128 GB",
                    "Rear Camera": "50MP + 50MP",
                    "Front Camera": "32MP",
                    "Battery": "5000 mAh",
                    "OS": "Android 14, Nothing OS 2.5",
                    "5G": "Yes",
                    "Weight": "190 g",
                },
                "prices": {"flipkart": 21999},
                "mrps": {"flipkart": 23999},
            },
            # Audio
            {
                "slug": "boat-airdopes-141-anc",
                "title": "boAt Airdopes 141 ANC TWS Earbuds",
                "brand": "boat",
                "category": "audio",
                "description": "boAt Airdopes 141 ANC with hybrid Active Noise Cancellation up to 32dB, 42 hours total playback, BEAST mode low latency, ENx quad mics, ASAP charge, IPX5.",
                "specs": {
                    "Driver": "10mm",
                    "ANC": "Hybrid, up to 32dB",
                    "Battery": "42 hrs total",
                    "Bluetooth": "5.3",
                    "Water Resistance": "IPX5",
                    "Charging": "USB-C, ASAP Charge",
                    "Weight": "4.5 g (per bud)",
                },
                "prices": {"amazon_in": 1299, "flipkart": 1349},
                "mrps": {"amazon_in": 4490, "flipkart": 4490},
            },
            {
                "slug": "sony-wh-1000xm5",
                "title": "Sony WH-1000XM5 Wireless Noise Cancelling Headphones",
                "brand": "sony",
                "category": "audio",
                "description": "Industry-leading noise cancellation with Auto NC Optimizer, two processors control 8 microphones, 30-hour battery, multipoint connection, speak-to-chat.",
                "specs": {
                    "Driver": "30mm",
                    "ANC": "Industry-leading, 8 mics",
                    "Battery": "30 hrs",
                    "Bluetooth": "5.2, LDAC, Multipoint",
                    "Weight": "250 g",
                    "Charging": "USB-C, 3 min = 3 hrs",
                    "Codec": "LDAC, AAC, SBC",
                },
                "prices": {"amazon_in": 22990, "flipkart": 23490, "croma": 24990},
                "mrps": {"amazon_in": 34990, "flipkart": 34990, "croma": 34990},
            },
            {
                "slug": "jbl-flip-6",
                "title": "JBL Flip 6 Portable Bluetooth Speaker",
                "brand": "jbl",
                "category": "audio",
                "description": "JBL Flip 6 delivers powerful JBL Original Pro Sound with an optimised racetrack-shaped driver, tweeter and dual passive radiators. IP67 waterproof and dustproof, 12 hours playtime.",
                "specs": {
                    "Driver": "Racetrack woofer + tweeter",
                    "Battery": "12 hrs",
                    "Bluetooth": "5.1",
                    "Waterproof": "IP67",
                    "PartyBoost": "Yes",
                    "Weight": "550 g",
                },
                "prices": {"amazon_in": 8499, "flipkart": 8999, "croma": 9499},
                "mrps": {"amazon_in": 14999, "flipkart": 14999, "croma": 14999},
            },
            {
                "slug": "noise-colorfit-pro-5",
                "title": "Noise ColorFit Pro 5 Smartwatch",
                "brand": "noise",
                "category": "smartwatches",
                "description": "Noise ColorFit Pro 5 with 1.85\" AMOLED display, Nebula UI, Tru Sync technology, smart gesture control, 100+ sports modes, heart rate, SpO2, stress monitoring.",
                "specs": {
                    "Display": "1.85\" AMOLED",
                    "Battery": "Up to 7 days",
                    "Water Resistance": "IP68",
                    "Sensors": "HR, SpO2, Stress",
                    "Sports Modes": "100+",
                    "Connectivity": "Bluetooth 5.3",
                    "Weight": "43 g",
                },
                "prices": {"amazon_in": 2999, "flipkart": 2799},
                "mrps": {"amazon_in": 5999, "flipkart": 5999},
            },
            # Laptops
            {
                "slug": "hp-pavilion-15-2024",
                "title": "HP Pavilion 15 (2024) Intel Core i5-1335U, 16GB RAM, 512GB SSD",
                "brand": "hp",
                "category": "laptops",
                "description": "HP Pavilion 15 with 13th Gen Intel Core i5, 15.6\" FHD IPS anti-glare display, 16GB DDR4 RAM, 512GB PCIe NVMe SSD, Intel Iris Xe Graphics, backlit keyboard.",
                "specs": {
                    "Display": "15.6\" FHD IPS, Anti-glare",
                    "Processor": "Intel Core i5-1335U",
                    "RAM": "16 GB DDR4",
                    "Storage": "512 GB NVMe SSD",
                    "Graphics": "Intel Iris Xe",
                    "OS": "Windows 11 Home",
                    "Battery": "Up to 8 hours",
                    "Weight": "1.75 kg",
                },
                "prices": {"amazon_in": 52990, "flipkart": 53490, "croma": 55990},
                "mrps": {"amazon_in": 67690, "flipkart": 67690, "croma": 67690},
            },
            {
                "slug": "macbook-air-m3",
                "title": "Apple MacBook Air 13\" M3 Chip (8GB RAM, 256GB SSD)",
                "brand": "apple",
                "category": "laptops",
                "description": "MacBook Air with M3 chip delivers faster performance with an 8-core CPU, 10-core GPU, and supports up to 2 external displays. 13.6\" Liquid Retina display, 18-hour battery.",
                "specs": {
                    "Display": "13.6\" Liquid Retina",
                    "Processor": "Apple M3 (8-core CPU, 10-core GPU)",
                    "RAM": "8 GB Unified",
                    "Storage": "256 GB SSD",
                    "OS": "macOS Sonoma",
                    "Battery": "Up to 18 hours",
                    "Weight": "1.24 kg",
                    "Ports": "2x Thunderbolt/USB 4, MagSafe 3",
                },
                "prices": {"amazon_in": 99990, "flipkart": 99990, "croma": 104990},
                "mrps": {"amazon_in": 114900, "flipkart": 114900, "croma": 114900},
            },
            # Appliances
            {
                "slug": "prestige-iris-750w-mixer",
                "title": "Prestige Iris 750W Mixer Grinder (3 Jars)",
                "brand": "prestige",
                "category": "kitchen-tools",
                "description": "Prestige Iris 750W mixer grinder with 3 stainless steel jars, super-efficient motor, easy-to-use 3-speed control with pulse function.",
                "specs": {
                    "Power": "750 W",
                    "Jars": "3 (Wet, Dry, Chutney)",
                    "Blade": "Stainless Steel",
                    "Speed": "3 speed + Pulse",
                    "Warranty": "2 years",
                },
                "prices": {"amazon_in": 2799, "flipkart": 2699},
                "mrps": {"amazon_in": 4595, "flipkart": 4595},
            },
            {
                "slug": "dyson-v12-detect-slim",
                "title": "Dyson V12 Detect Slim Absolute Cordless Vacuum",
                "brand": "dyson",
                "category": "appliances",
                "description": "Dyson V12 Detect Slim with laser dust detection, piezo sensor, auto-adjusting suction, HEPA filtration, LCD screen showing real-time dust count.",
                "specs": {
                    "Suction": "150 AW",
                    "Runtime": "Up to 60 min",
                    "Bin Volume": "0.35 L",
                    "Weight": "2.2 kg",
                    "Filtration": "Whole-machine HEPA",
                    "Laser": "Green laser dust detection",
                },
                "prices": {"amazon_in": 46990, "flipkart": 47990},
                "mrps": {"amazon_in": 58900, "flipkart": 58900},
            },
            {
                "slug": "daikin-1-5t-5-star-inverter-ac",
                "title": "Daikin 1.5 Ton 5 Star Inverter Split AC (2024 Model)",
                "brand": "daikin",
                "category": "air-conditioners",
                "description": "Daikin 1.5 ton 5 star inverter split AC with PM 2.5 filter, Coanda airflow, Dew Clean technology, stabilizer-free operation (130V-264V), R-32 refrigerant.",
                "specs": {
                    "Capacity": "1.5 Ton",
                    "Star Rating": "5 Star",
                    "Type": "Inverter Split",
                    "Refrigerant": "R-32",
                    "ISEER": "5.2",
                    "Annual Energy": "829 kWh",
                    "Noise Level": "35 dB (indoor)",
                    "Warranty": "1 yr product + 5 yr compressor",
                },
                "prices": {"amazon_in": 44990, "flipkart": 43990, "croma": 47990},
                "mrps": {"amazon_in": 62990, "flipkart": 62990, "croma": 62990},
            },
            {
                "slug": "samsung-653l-frost-free-fridge",
                "title": "Samsung 653L Frost Free Side by Side Refrigerator",
                "brand": "samsung",
                "category": "refrigerators",
                "description": "Samsung 653L Side by Side with SpaceMax Technology, Digital Inverter Compressor, All-Around Cooling, Power Cool/Freeze, convertible 5-in-1 modes.",
                "specs": {
                    "Capacity": "653 L",
                    "Type": "Side by Side",
                    "Star Rating": "3 Star",
                    "Compressor": "Digital Inverter",
                    "Cooling": "All-Around Cooling",
                    "Convertible": "5-in-1 modes",
                    "Warranty": "1 yr product + 20 yr compressor",
                },
                "prices": {"amazon_in": 69990, "flipkart": 67990},
                "mrps": {"amazon_in": 101990, "flipkart": 101990},
            },
            {
                "slug": "lg-8kg-front-load-washer",
                "title": "LG 8 Kg 5 Star AI Direct Drive Front Load Washing Machine",
                "brand": "lg",
                "category": "washing-machines",
                "description": "LG 8 kg front load with AI DD (AI Direct Drive) technology that detects fabric type and optimises wash motion. Steam wash, ThinQ (Wi-Fi), Allergy Care, 6 Motion Technology.",
                "specs": {
                    "Capacity": "8 Kg",
                    "Type": "Front Load",
                    "Star Rating": "5 Star",
                    "Motor": "AI Direct Drive",
                    "Max Spin": "1400 RPM",
                    "Steam": "Yes",
                    "Smart": "ThinQ Wi-Fi",
                    "Warranty": "2 yr product + 10 yr motor",
                },
                "prices": {"amazon_in": 38990, "flipkart": 37990, "croma": 39990},
                "mrps": {"amazon_in": 53990, "flipkart": 53990, "croma": 53990},
            },
            # TVs
            {
                "slug": "samsung-55-crystal-4k-uhd",
                "title": "Samsung 55\" Crystal 4K UHD Smart TV (2024)",
                "brand": "samsung",
                "category": "televisions",
                "description": "Samsung 55-inch Crystal 4K UHD with Crystal Processor 4K, Dynamic Crystal Color, Smart Hub, Gaming Hub, built-in Alexa and Bixby.",
                "specs": {
                    "Screen": "55\"",
                    "Resolution": "4K UHD (3840x2160)",
                    "Processor": "Crystal Processor 4K",
                    "HDR": "HDR10+",
                    "Smart TV": "Tizen OS",
                    "Sound": "20W, 2ch",
                    "HDMI": "3 ports",
                },
                "prices": {"amazon_in": 39990, "flipkart": 38990, "croma": 42990},
                "mrps": {"amazon_in": 64900, "flipkart": 64900, "croma": 64900},
            },
            {
                "slug": "sony-bravia-65-4k-google-tv",
                "title": "Sony Bravia 65\" 4K Ultra HD Google TV (2024)",
                "brand": "sony",
                "category": "televisions",
                "description": "Sony Bravia 65\" 4K with X1 4K Processor, Triluminos Pro display, Dolby Vision & Atmos, Google TV, Chromecast built-in, Apple AirPlay 2.",
                "specs": {
                    "Screen": "65\"",
                    "Resolution": "4K UHD (3840x2160)",
                    "Processor": "X1 4K Processor",
                    "HDR": "Dolby Vision, HDR10, HLG",
                    "Smart TV": "Google TV",
                    "Sound": "20W, Dolby Atmos",
                    "HDMI": "4 ports (1 eARC)",
                },
                "prices": {"amazon_in": 82990, "croma": 84990},
                "mrps": {"amazon_in": 139900, "croma": 139900},
            },
            # Tablets
            {
                "slug": "samsung-galaxy-tab-s9-fe",
                "title": "Samsung Galaxy Tab S9 FE Wi-Fi (6GB RAM, 128GB)",
                "brand": "samsung",
                "category": "tablets",
                "description": "Galaxy Tab S9 FE with 10.9\" TFT display, Exynos 1380, IP68 water resistance, S Pen included, 8000mAh battery, DeX mode.",
                "specs": {
                    "Display": "10.9\" TFT, 90Hz",
                    "Processor": "Exynos 1380",
                    "RAM": "6 GB",
                    "Storage": "128 GB",
                    "S Pen": "Included",
                    "Battery": "8000 mAh",
                    "Water Resistance": "IP68",
                    "OS": "Android 14",
                },
                "prices": {"amazon_in": 26999, "flipkart": 27499, "croma": 29999},
                "mrps": {"amazon_in": 44999, "flipkart": 44999, "croma": 44999},
            },
            # More Audio
            {
                "slug": "sennheiser-momentum-4",
                "title": "Sennheiser Momentum 4 Wireless Headphones",
                "brand": "sennheiser",
                "category": "audio",
                "description": "Sennheiser Momentum 4 with Adaptive Noise Cancellation, 60-hour battery, aptX Adaptive, Audiophile sound, foldable design.",
                "specs": {
                    "Driver": "42mm",
                    "ANC": "Adaptive",
                    "Battery": "60 hrs",
                    "Bluetooth": "5.2, aptX Adaptive",
                    "Weight": "293 g",
                    "Codec": "aptX Adaptive, AAC, SBC",
                },
                "prices": {"amazon_in": 24990, "croma": 26990},
                "mrps": {"amazon_in": 34990, "croma": 34990},
            },
            # More Laptops
            {
                "slug": "asus-vivobook-15-2024",
                "title": "ASUS Vivobook 15 (2024) AMD Ryzen 5 7530U, 16GB, 512GB",
                "brand": "asus",
                "category": "laptops",
                "description": "ASUS Vivobook 15 with AMD Ryzen 5 7530U, 15.6\" FHD IPS display, 16GB DDR4, 512GB NVMe SSD, fingerprint reader, 180-degree hinge.",
                "specs": {
                    "Display": "15.6\" FHD IPS",
                    "Processor": "AMD Ryzen 5 7530U",
                    "RAM": "16 GB DDR4",
                    "Storage": "512 GB NVMe SSD",
                    "Graphics": "AMD Radeon",
                    "OS": "Windows 11 Home",
                    "Battery": "Up to 8 hours",
                    "Weight": "1.7 kg",
                },
                "prices": {"amazon_in": 44990, "flipkart": 45990},
                "mrps": {"amazon_in": 62990, "flipkart": 62990},
            },
            # More Smartphones
            {
                "slug": "google-pixel-8a",
                "title": "Google Pixel 8a 5G (8GB RAM, 128GB)",
                "brand": "google",
                "category": "smartphones",
                "description": "Pixel 8a with Tensor G3 chip, 7 years of OS & security updates, 6.1\" Actua OLED display, 64MP camera with Magic Eraser, Real Tone, Night Sight.",
                "specs": {
                    "Display": "6.1\" Actua OLED, 120Hz",
                    "Processor": "Google Tensor G3",
                    "RAM": "8 GB",
                    "Storage": "128 GB",
                    "Rear Camera": "64MP + 13MP",
                    "Front Camera": "13MP",
                    "Battery": "4492 mAh",
                    "OS": "Android 14",
                    "5G": "Yes",
                    "Weight": "188 g",
                },
                "prices": {"amazon_in": 37999, "flipkart": 37999},
                "mrps": {"amazon_in": 52999, "flipkart": 52999},
            },
            {
                "slug": "motorola-edge-50-pro",
                "title": "Motorola Edge 50 Pro 5G (12GB RAM, 256GB)",
                "brand": "motorola",
                "category": "smartphones",
                "description": "Motorola Edge 50 Pro with Snapdragon 7 Gen 3, 6.7\" pOLED 144Hz, 50MP + 13MP + 10MP cameras, 4500mAh battery, 125W TurboPower charging.",
                "specs": {
                    "Display": "6.7\" pOLED, 144Hz",
                    "Processor": "Snapdragon 7 Gen 3",
                    "RAM": "12 GB",
                    "Storage": "256 GB",
                    "Rear Camera": "50MP + 13MP + 10MP",
                    "Front Camera": "50MP",
                    "Battery": "4500 mAh",
                    "OS": "Android 14",
                    "5G": "Yes",
                    "Weight": "186 g",
                },
                "prices": {"flipkart": 27999},
                "mrps": {"flipkart": 35999},
            },
            # Home appliances
            {
                "slug": "havells-1200mm-ceiling-fan",
                "title": "Havells Efficiencia Neo 1200mm BLDC Ceiling Fan",
                "brand": "havells",
                "category": "appliances",
                "description": "Havells Efficiencia Neo BLDC motor ceiling fan with remote control, energy saving (28W), 1200mm sweep, 5 star rated, inverter compatible.",
                "specs": {
                    "Sweep": "1200 mm",
                    "Motor": "BLDC",
                    "Power": "28 W",
                    "Star Rating": "5 Star",
                    "Speed": "5 levels + Remote",
                    "Air Delivery": "230 CMM",
                    "Warranty": "2 years",
                },
                "prices": {"amazon_in": 3599, "flipkart": 3499},
                "mrps": {"amazon_in": 5600, "flipkart": 5600},
            },
            {
                "slug": "bajaj-majesty-otg-25l",
                "title": "Bajaj Majesty 2500 TMCSS 25L Oven Toaster Grill",
                "brand": "bajaj",
                "category": "kitchen-tools",
                "description": "Bajaj Majesty 25L OTG with motorised rotisserie, 6 heating modes, 60-minute timer, illuminated chamber, 1600W power.",
                "specs": {
                    "Capacity": "25 L",
                    "Power": "1600 W",
                    "Modes": "6 heating modes",
                    "Rotisserie": "Motorised",
                    "Timer": "60 min",
                    "Accessories": "Baking tray, grill rack, crumb tray, skewer rod",
                },
                "prices": {"amazon_in": 5999, "flipkart": 5799},
                "mrps": {"amazon_in": 9000, "flipkart": 9000},
            },
            {
                "slug": "philips-air-fryer-hd9200",
                "title": "Philips Air Fryer HD9200/90 (4.1L)",
                "brand": "philips",
                "category": "kitchen-tools",
                "description": "Philips Essential Air Fryer with Rapid Air technology for crispy food with up to 90% less fat. 4.1L capacity, 7 presets, touch screen, dishwasher-safe basket.",
                "specs": {
                    "Capacity": "4.1 L",
                    "Power": "1400 W",
                    "Technology": "Rapid Air",
                    "Presets": "7",
                    "Timer": "60 min",
                    "Temperature": "80-200°C",
                },
                "prices": {"amazon_in": 6999, "flipkart": 7299, "croma": 7499},
                "mrps": {"amazon_in": 11995, "flipkart": 11995, "croma": 11995},
            },
            # Cameras
            {
                "slug": "sony-alpha-a6400",
                "title": "Sony Alpha A6400 Mirrorless Camera (Body Only)",
                "brand": "sony",
                "category": "cameras",
                "description": "Sony A6400 with 24.2MP APS-C Exmor CMOS sensor, Real-time Eye AF, Real-time Tracking, 4K video, 180-degree tiltable touchscreen, 0.02s AF.",
                "specs": {
                    "Sensor": "24.2MP APS-C Exmor CMOS",
                    "AF": "425-point phase detection, 0.02s",
                    "ISO": "100-32000 (expandable to 102400)",
                    "Video": "4K 30fps, 1080p 120fps",
                    "Screen": "3\" 180° tiltable touchscreen",
                    "EVF": "2.36M dots OLED",
                    "Weight": "403 g",
                },
                "prices": {"amazon_in": 72990, "croma": 74990},
                "mrps": {"amazon_in": 84990, "croma": 84990},
            },
            # More smartwatches
            {
                "slug": "apple-watch-se-2024",
                "title": "Apple Watch SE (2024) GPS 40mm",
                "brand": "apple",
                "category": "smartwatches",
                "description": "Apple Watch SE with S8 SiP chip, OLED Retina display, crash detection, fall detection, heart rate monitoring, workout tracking, water resistant 50m.",
                "specs": {
                    "Display": "40mm OLED Retina",
                    "Chip": "S8 SiP",
                    "Sensors": "HR, Accelerometer, Gyroscope",
                    "Water Resistance": "50m (WR50)",
                    "Battery": "Up to 18 hours",
                    "Connectivity": "GPS, Wi-Fi, Bluetooth 5.3",
                    "OS": "watchOS 11",
                },
                "prices": {"amazon_in": 24990, "flipkart": 24990, "croma": 26900},
                "mrps": {"amazon_in": 29900, "flipkart": 29900, "croma": 29900},
            },
            {
                "slug": "realme-12-pro-plus",
                "title": "Realme 12 Pro+ 5G (8GB RAM, 256GB)",
                "brand": "realme",
                "category": "smartphones",
                "description": "Realme 12 Pro+ with Sony IMX890 50MP OIS periscope telephoto, Snapdragon 7s Gen 2, 6.7\" 120Hz curved display, 5000mAh, 67W SUPERVOOC.",
                "specs": {
                    "Display": "6.7\" Curved AMOLED, 120Hz",
                    "Processor": "Snapdragon 7s Gen 2",
                    "RAM": "8 GB",
                    "Storage": "256 GB",
                    "Rear Camera": "50MP + 8MP + 64MP Periscope",
                    "Front Camera": "32MP",
                    "Battery": "5000 mAh",
                    "OS": "Android 14, Realme UI 5",
                    "5G": "Yes",
                    "Weight": "190 g",
                },
                "prices": {"amazon_in": 24999, "flipkart": 24999},
                "mrps": {"amazon_in": 30999, "flipkart": 30999},
            },
            # Voltas AC
            {
                "slug": "voltas-1t-3-star-inverter-ac",
                "title": "Voltas 1 Ton 3 Star Inverter Split AC (2024 Model)",
                "brand": "voltas",
                "category": "air-conditioners",
                "description": "Voltas 1 ton 3 star inverter split AC with copper condenser, 4-in-1 adjustable mode, dust filter, self-diagnosis, stabilizer-free operation.",
                "specs": {
                    "Capacity": "1 Ton",
                    "Star Rating": "3 Star",
                    "Type": "Inverter Split",
                    "Refrigerant": "R-32",
                    "Annual Energy": "956 kWh",
                    "Condenser": "Copper",
                    "Warranty": "1 yr product + 5 yr compressor",
                },
                "prices": {"amazon_in": 29990, "flipkart": 28990, "croma": 31990},
                "mrps": {"amazon_in": 46990, "flipkart": 46990, "croma": 46990},
            },
            # Whirlpool Fridge
            {
                "slug": "whirlpool-265l-frost-free-fridge",
                "title": "Whirlpool 265L 3 Star Frost Free Double Door Refrigerator",
                "brand": "whirlpool",
                "category": "refrigerators",
                "description": "Whirlpool 265L with 6th Sense ActiveFresh technology, IntelliFresh inverter, Zeolite technology for up to 12 days garden freshness.",
                "specs": {
                    "Capacity": "265 L",
                    "Type": "Double Door",
                    "Star Rating": "3 Star",
                    "Compressor": "IntelliFresh Inverter",
                    "Technology": "6th Sense ActiveFresh",
                    "Warranty": "1 yr product + 10 yr compressor",
                },
                "prices": {"amazon_in": 24990, "flipkart": 23990},
                "mrps": {"amazon_in": 35650, "flipkart": 35650},
            },
        ]

        products = {}
        for p in PRODUCTS:
            obj, _ = Product.objects.update_or_create(
                slug=p["slug"],
                defaults=dict(
                    title=p["title"],
                    brand=brands[p["brand"]],
                    category=cats[p["category"]],
                    description=p["description"],
                    specs=p["specs"],
                    images=[f"https://placehold.co/600x600/f8f8f8/333?text={p['slug'].split('-')[0].upper()}"],
                    status="active",
                    dud_score=Decimal(str(random.randint(55, 95))) + Decimal("0.00"),
                    dud_score_confidence=random.choice(["medium", "high", "very_high"]),
                    dud_score_updated_at=_dt(random.randint(1, 7)),
                    avg_rating=Decimal(str(round(random.uniform(3.5, 4.8), 2))),
                    total_reviews=random.randint(50, 5000),
                    is_refurbished=False,
                    last_scraped_at=_dt(0),
                ),
            )
            obj._seed_prices = p.get("prices", {})
            obj._seed_mrps = p.get("mrps", {})
            products[p["slug"]] = obj
        self.stdout.write(f"  Products: {len(products)}")

        # Update category product counts
        for cat in cats.values():
            cat.product_count = Product.objects.filter(category=cat).count()
            cat.save(update_fields=["product_count"])

        return products

    # ── Sellers ───────────────────────────────────────────────────

    def _seed_sellers(self, marketplaces):
        SELLERS = [
            ("amazon_in", "Appario Retail Private Ltd", "APPARIORETAIL", 4.2, 93.5, True),
            ("amazon_in", "Cloudtail India Private Limited", "CLOUDTAIL", 4.3, 95.0, True),
            ("amazon_in", "RetailNet", "RETAILNET", 4.1, 91.0, True),
            ("amazon_in", "SuperComNet", "SUPERCOMNET", 4.0, 90.0, True),
            ("amazon_in", "Cocoblu Retail", "COCOBLU", 3.9, 88.5, True),
            ("amazon_in", "TrueComRetail", "TRUECOMRETAIL", 4.4, 94.0, True),
            ("amazon_in", "Darshita Electronics", "DARSHITA", 3.8, 86.0, False),
            ("flipkart", "RetailNet (Flipkart)", "RETAILNET_FK", 4.3, 94.0, True),
            ("flipkart", "SuperComNet (Flipkart)", "SUPERCOM_FK", 4.1, 92.0, True),
            ("flipkart", "OmniTechRetail", "OMNI_FK", 3.9, 89.0, True),
            ("flipkart", "TBSWorld", "TBSWORLD", 4.0, 90.5, False),
            ("flipkart", "Spice Mobility", "SPICE_FK", 3.7, 85.0, False),
            ("croma", "Croma (Official)", "CROMA_OFFICIAL", 4.5, 97.0, True),
            ("reliance_digital", "Reliance Retail", "RELIANCE_RETAIL", 4.4, 96.0, True),
        ]
        sellers = {}
        for mp_slug, name, ext_id, rating, pos_pct, verified in SELLERS:
            if mp_slug not in marketplaces:
                continue
            obj, _ = Seller.objects.update_or_create(
                marketplace=marketplaces[mp_slug],
                external_seller_id=ext_id,
                defaults=dict(
                    name=name,
                    avg_rating=Decimal(str(rating)),
                    total_ratings=random.randint(5000, 50000),
                    positive_pct=Decimal(str(pos_pct)),
                    is_verified=verified,
                    seller_since=date(random.randint(2018, 2023), random.randint(1, 12), 1),
                ),
            )
            sellers[(mp_slug, ext_id)] = obj
        self.stdout.write(f"  Sellers: {len(sellers)}")
        return sellers

    # ── Product Listings ──────────────────────────────────────────

    def _seed_listings(self, products, marketplaces, sellers):
        # Map marketplace → likely sellers
        mp_sellers = {
            "amazon_in": [s for k, s in sellers.items() if k[0] == "amazon_in"],
            "flipkart": [s for k, s in sellers.items() if k[0] == "flipkart"],
            "croma": [s for k, s in sellers.items() if k[0] == "croma"],
        }

        listings = []
        for slug, product in products.items():
            prices = getattr(product, "_seed_prices", {})
            mrps = getattr(product, "_seed_mrps", {})
            best_price = None
            best_mp = ""

            for mp_slug, price_rupees in prices.items():
                if mp_slug not in marketplaces:
                    continue
                mp = marketplaces[mp_slug]
                mrp = mrps.get(mp_slug, int(price_rupees * 1.3))
                price_paisa = _paisa(price_rupees)
                mrp_paisa = _paisa(mrp)
                disc = round((1 - price_rupees / mrp) * 100, 2) if mrp > price_rupees else 0

                seller_pool = mp_sellers.get(mp_slug, [])
                seller = random.choice(seller_pool) if seller_pool else None

                obj, _ = ProductListing.objects.update_or_create(
                    marketplace=mp,
                    external_id=f"{mp_slug}_{slug}",
                    defaults=dict(
                        product=product,
                        seller=seller,
                        external_url=f"https://{mp.base_url}/dp/{slug}",
                        title=product.title,
                        current_price=price_paisa,
                        mrp=mrp_paisa,
                        discount_pct=Decimal(str(disc)),
                        in_stock=True,
                        rating=product.avg_rating,
                        review_count=random.randint(100, 3000),
                        match_confidence=Decimal("0.99"),
                        match_method="exact_sku",
                        last_scraped_at=_dt(0),
                    ),
                )
                listings.append(obj)

                if best_price is None or price_paisa < best_price:
                    best_price = price_paisa
                    best_mp = mp.name

            # Update product denormalized fields
            if best_price is not None:
                product.current_best_price = best_price
                product.current_best_marketplace = best_mp
                product.lowest_price_ever = best_price - _rand_paisa(0, 500)
                product.lowest_price_date = (_dt(random.randint(30, 90))).date()
                product.save(update_fields=[
                    "current_best_price", "current_best_marketplace",
                    "lowest_price_ever", "lowest_price_date",
                ])

        self.stdout.write(f"  Listings: {len(listings)}")
        return listings

    # ── Price Snapshots ───────────────────────────────────────────

    def _seed_price_snapshots(self, listings, products, marketplaces):
        """Generate 90 days of daily price snapshots for each listing.
        Uses raw SQL because PriceSnapshot is managed=False (no id column).
        """
        now = timezone.now()
        rows = []

        for listing in listings:
            base_price = float(listing.current_price)
            for day in range(90, -1, -1):
                variance = random.uniform(-0.10, 0.10)
                price = round(base_price * (1 + variance), 2)
                mrp = float(listing.mrp or base_price * 1.3)
                disc = round((1 - price / mrp) * 100, 2) if mrp > price else 0
                t = now - timedelta(days=day, hours=random.randint(0, 12))
                seller_name = listing.seller.name if listing.seller else ""

                rows.append((
                    t, str(listing.id), str(listing.product_id),
                    listing.marketplace_id, price, mrp, disc,
                    random.random() > 0.05, seller_name,
                ))

        # Raw SQL insert — no RETURNING id
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO price_snapshots
                    (time, listing_id, product_id, marketplace_id,
                     price, mrp, discount_pct, in_stock, seller_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.executemany(sql, rows)

        self.stdout.write(f"  Price Snapshots: {len(rows)}")

    # ── Reviews ───────────────────────────────────────────────────

    def _seed_reviews(self, listings, products):
        NAMES = [
            "Rahul Sharma", "Priya Patel", "Amit Kumar", "Sneha Gupta",
            "Vikram Singh", "Anita Desai", "Rajesh Nair", "Meera Iyer",
            "Karthik Reddy", "Sunita Menon", "Deepak Joshi", "Pooja Kapoor",
            "Suresh Verma", "Nisha Agarwal", "Arun Pillai", "Kavita Rao",
            "Manoj Tiwari", "Divya Chopra", "Sanjay Mishra", "Lakshmi Devi",
        ]
        TITLES_GOOD = [
            "Excellent product, highly recommend!",
            "Worth every rupee",
            "Best in this price range",
            "Amazing quality and performance",
            "Very satisfied with this purchase",
            "Great value for money",
            "Superb build quality",
            "Exceeded my expectations",
        ]
        TITLES_OK = [
            "Decent product, could be better",
            "Good for the price",
            "Average performance",
            "Does the job",
            "Okay product, nothing special",
        ]
        TITLES_BAD = [
            "Not worth the price",
            "Disappointed with quality",
            "Below expectations",
            "Would not recommend",
        ]
        BODIES_GOOD = [
            "I've been using this for over a month now and I'm thoroughly impressed. The build quality is excellent and performance is top-notch. Definitely recommend this to anyone looking for a reliable product.",
            "After extensive research, I chose this over competitors and I'm glad I did. The features are exactly as described and the overall experience has been fantastic. Great purchase!",
            "This is my second purchase of this brand and they never disappoint. Excellent packaging, fast delivery, and the product itself is brilliant. Five stars all the way!",
            "Bought this during a sale and got amazing value. The performance exceeds what I expected at this price point. Battery life is especially impressive.",
        ]
        BODIES_OK = [
            "It's a decent product for the price. Nothing extraordinary but gets the job done. The build could be slightly better but overall acceptable quality.",
            "Works as expected. Not the best in market but definitely not the worst either. Good enough for daily use. Would have liked better customer support.",
            "Average experience overall. Some features work great while others are just okay. For the price you pay, it's a fair deal.",
        ]
        BODIES_BAD = [
            "Very disappointed with this purchase. The quality doesn't match the advertising at all. Had multiple issues within the first week of use.",
            "Not recommended. The product stopped working properly after just 2 weeks. Customer service was unhelpful. Save your money.",
        ]
        PROS = [
            ["Good build quality", "Fast performance", "Value for money"],
            ["Great battery life", "Beautiful display", "Smooth UI"],
            ["Excellent camera", "Premium feel", "Good speaker output"],
            ["Lightweight", "Fast charging", "Reliable brand"],
            ["Good sound quality", "Comfortable fit", "Long battery"],
        ]
        CONS = [
            ["Average camera in low light", "No expandable storage"],
            ["Slightly heavy", "Heating during gaming"],
            ["No headphone jack", "Bloatware"],
            ["Average speaker", "Slow charging"],
            ["No wireless charging", "Plastic body"],
        ]

        reviews = []
        for listing in listings:
            num_reviews = random.randint(3, 6)
            for _ in range(num_reviews):
                rating = random.choices([5, 4, 3, 2, 1], weights=[35, 30, 20, 10, 5])[0]
                if rating >= 4:
                    title = random.choice(TITLES_GOOD)
                    body = random.choice(BODIES_GOOD)
                elif rating == 3:
                    title = random.choice(TITLES_OK)
                    body = random.choice(BODIES_OK)
                else:
                    title = random.choice(TITLES_BAD)
                    body = random.choice(BODIES_BAD)

                sentiment = round(random.uniform(0.6, 0.95), 2) if rating >= 4 else (
                    round(random.uniform(0.3, 0.6), 2) if rating == 3 else
                    round(random.uniform(0.05, 0.3), 2)
                )
                sentiment_label = "positive" if sentiment > 0.6 else ("neutral" if sentiment > 0.3 else "negative")

                reviews.append(Review(
                    listing=listing,
                    product=listing.product,
                    external_review_id=f"rev_{uuid.uuid4().hex[:12]}",
                    reviewer_name=random.choice(NAMES),
                    rating=rating,
                    title=title,
                    body=body,
                    is_verified_purchase=random.random() > 0.2,
                    review_date=(_dt(random.randint(1, 180))).date(),
                    helpful_votes=random.randint(0, 200),
                    sentiment_score=Decimal(str(sentiment)),
                    sentiment_label=sentiment_label,
                    extracted_pros=random.choice(PROS) if rating >= 3 else [],
                    extracted_cons=random.choice(CONS) if rating <= 4 else [],
                    credibility_score=Decimal(str(round(random.uniform(0.5, 0.98), 2))),
                    is_flagged=random.random() < 0.05,
                    fraud_flags=["duplicate_content"] if random.random() < 0.03 else [],
                    upvotes=random.randint(0, 100),
                    downvotes=random.randint(0, 20),
                    vote_score=random.randint(-5, 100),
                ))

        Review.objects.bulk_create(reviews, batch_size=500)
        self.stdout.write(f"  Reviews: {len(reviews)}")

    # ── Update Product Stats ──────────────────────────────────────

    def _update_product_stats(self, products):
        """Recalculate avg_rating and total_reviews from actual reviews."""
        from django.db.models import Avg, Count

        for product in products.values():
            stats = Review.objects.filter(product=product).aggregate(
                avg=Avg("rating"), count=Count("id"),
            )
            if stats["count"] > 0:
                product.avg_rating = Decimal(str(round(float(stats["avg"]), 2)))
                product.total_reviews = stats["count"]
                product.save(update_fields=["avg_rating", "total_reviews"])

    # ── Bank Cards ────────────────────────────────────────────────

    def _seed_bank_cards(self):
        CARDS = [
            ("hdfc", "HDFC Bank", "Regalia", "credit_card", "visa", False, 3.3),
            ("hdfc", "HDFC Bank", "Millennia", "credit_card", "mastercard", False, 5.0),
            ("hdfc", "HDFC Bank", "MoneyBack+", "debit_card", "visa", False, 1.0),
            ("icici", "ICICI Bank", "Amazon Pay Credit Card", "credit_card", "visa", True, 5.0),
            ("icici", "ICICI Bank", "Coral", "credit_card", "visa", False, 2.0),
            ("sbi", "SBI", "SimplyCLICK", "credit_card", "visa", False, 10.0),
            ("sbi", "SBI", "Cashback", "credit_card", "visa", False, 5.0),
            ("axis", "Axis Bank", "Flipkart Credit Card", "credit_card", "visa", True, 5.0),
            ("axis", "Axis Bank", "ACE", "credit_card", "visa", False, 2.0),
            ("kotak", "Kotak Mahindra", "811 Dream Different", "credit_card", "visa", False, 1.5),
        ]
        for bank_slug, bank_name, variant, card_type, network, co_brand, cashback in CARDS:
            BankCard.objects.update_or_create(
                bank_slug=bank_slug,
                card_variant=variant,
                card_type=card_type,
                defaults=dict(
                    bank_name=bank_name,
                    card_network=network,
                    is_co_branded=co_brand,
                    default_cashback_pct=Decimal(str(cashback)),
                    logo_url=f"https://placehold.co/120x40/eee/333?text={bank_slug.upper()}",
                ),
            )
        self.stdout.write(f"  Bank Cards: {len(CARDS)}")

    # ── Marketplace Offers ────────────────────────────────────────

    def _seed_marketplace_offers(self, marketplaces, categories):
        OFFERS = [
            {
                "mp": "amazon_in",
                "scope_type": "marketplace",
                "offer_type": "bank_instant_discount",
                "title": "10% Instant Discount with HDFC Credit Card",
                "bank_slug": "hdfc",
                "card_type": "credit_card",
                "card_variants": ["Regalia", "Millennia", "Infinia"],
                "discount_type": "percent",
                "discount_value": 10,
                "max_discount": 150000,
                "min_purchase": 500000,
            },
            {
                "mp": "amazon_in",
                "scope_type": "marketplace",
                "offer_type": "bank_instant_discount",
                "title": "5% Cashback with Amazon Pay ICICI Credit Card",
                "bank_slug": "icici",
                "card_type": "credit_card",
                "card_variants": ["Amazon Pay Credit Card"],
                "discount_type": "cashback",
                "discount_value": 5,
                "max_discount": 100000,
            },
            {
                "mp": "flipkart",
                "scope_type": "marketplace",
                "offer_type": "bank_instant_discount",
                "title": "10% Instant Discount with Axis Flipkart Card",
                "bank_slug": "axis",
                "card_type": "credit_card",
                "card_variants": ["Flipkart Credit Card"],
                "discount_type": "percent",
                "discount_value": 10,
                "max_discount": 150000,
                "min_purchase": 500000,
            },
            {
                "mp": "amazon_in",
                "scope_type": "marketplace",
                "offer_type": "no_cost_emi",
                "title": "No Cost EMI available on select cards",
                "discount_type": "no_cost_emi",
                "discount_value": 0,
                "emi_tenures": [3, 6, 9, 12],
            },
            {
                "mp": "flipkart",
                "scope_type": "marketplace",
                "offer_type": "no_cost_emi",
                "title": "No Cost EMI starting ₹1,667/month",
                "discount_type": "no_cost_emi",
                "discount_value": 0,
                "emi_tenures": [3, 6, 9],
            },
            {
                "mp": "amazon_in",
                "scope_type": "marketplace",
                "offer_type": "bank_instant_discount",
                "title": "₹1500 Instant Discount with SBI Credit Card",
                "bank_slug": "sbi",
                "card_type": "credit_card",
                "card_variants": ["SimplyCLICK", "Cashback"],
                "discount_type": "flat",
                "discount_value": 150000,
                "min_purchase": 2000000,
            },
            {
                "mp": "croma",
                "scope_type": "marketplace",
                "offer_type": "bank_instant_discount",
                "title": "₹2000 Off on HDFC Bank Debit & Credit Cards",
                "bank_slug": "hdfc",
                "card_type": "credit_card",
                "card_variants": [],
                "discount_type": "flat",
                "discount_value": 200000,
                "min_purchase": 1000000,
            },
        ]

        count = 0
        for o in OFFERS:
            mp_slug = o.pop("mp")
            if mp_slug not in marketplaces:
                continue
            MarketplaceOffer.objects.create(
                marketplace=marketplaces[mp_slug],
                scope_type=o.get("scope_type", "marketplace"),
                offer_type=o.get("offer_type", "bank_instant_discount"),
                title=o["title"],
                bank_slug=o.get("bank_slug", ""),
                card_type=o.get("card_type", ""),
                card_variants=o.get("card_variants", []),
                discount_type=o["discount_type"],
                discount_value=Decimal(str(o["discount_value"])),
                max_discount=_paisa(o["max_discount"] / 100) if o.get("max_discount") else None,
                min_purchase=_paisa(o["min_purchase"] / 100) if o.get("min_purchase") else None,
                emi_tenures=o.get("emi_tenures", []),
                valid_from=date.today() - timedelta(days=7),
                valid_until=date.today() + timedelta(days=30),
                is_active=True,
                source="scraped",
                last_verified_at=_dt(0),
            )
            count += 1
        self.stdout.write(f"  Marketplace Offers: {count}")

    # ── Deals ─────────────────────────────────────────────────────

    def _seed_deals(self, products, listings, marketplaces):
        product_list = list(products.values())
        deal_products = random.sample(product_list, min(15, len(product_list)))

        count = 0
        for product in deal_products:
            listing = ProductListing.objects.filter(product=product).first()
            if not listing:
                continue

            deal_type = random.choice(["error_price", "lowest_ever", "genuine_discount", "flash_sale"])
            ref_price = float(listing.mrp or listing.current_price * Decimal("1.3"))
            if deal_type == "error_price":
                cur_price = ref_price * random.uniform(0.3, 0.5)
            elif deal_type == "lowest_ever":
                cur_price = ref_price * random.uniform(0.5, 0.65)
            else:
                cur_price = ref_price * random.uniform(0.65, 0.85)

            disc_pct = round((1 - cur_price / ref_price) * 100, 2) if ref_price > 0 else 0

            Deal.objects.create(
                product=product,
                listing=listing,
                marketplace=listing.marketplace,
                deal_type=deal_type,
                current_price=Decimal(str(round(cur_price, 2))),
                reference_price=Decimal(str(round(ref_price, 2))),
                discount_pct=Decimal(str(disc_pct)),
                confidence=random.choice(["high", "medium", "low"]),
                is_active=True,
                expires_at=_dt(-random.randint(1, 7)),
                views=random.randint(100, 5000),
                clicks=random.randint(10, 500),
            )
            count += 1
        self.stdout.write(f"  Deals: {count}")

    # ── DudScore Config ───────────────────────────────────────────

    def _seed_dudscore_config(self):
        DudScoreConfig.objects.update_or_create(
            version=1,
            defaults=dict(
                w_sentiment=Decimal("0.200"),
                w_rating_quality=Decimal("0.200"),
                w_price_value=Decimal("0.150"),
                w_review_credibility=Decimal("0.200"),
                w_price_stability=Decimal("0.150"),
                w_return_signal=Decimal("0.100"),
                fraud_penalty_threshold=Decimal("0.30"),
                min_review_threshold=5,
                cold_start_penalty=Decimal("0.20"),
                anomaly_spike_threshold=Decimal("50.00"),
                is_active=True,
                activated_at=_dt(30),
                change_reason="Initial production config v1",
            ),
        )
        self.stdout.write("  DudScore Config: 1")

    # ── DudScore History ──────────────────────────────────────────

    def _seed_dudscore_history(self, products):
        """Uses raw SQL because DudScoreHistory is managed=False (no id column)."""
        import json

        now = timezone.now()
        rows = []
        for product in products.values():
            base_score = float(product.dud_score or 75)
            for week in range(12, -1, -1):
                score = base_score + random.uniform(-5, 5)
                score = max(10, min(100, score))
                components = json.dumps({
                    "sentiment": round(random.uniform(50, 95), 2),
                    "rating_quality": round(random.uniform(50, 95), 2),
                    "price_value": round(random.uniform(50, 95), 2),
                    "review_credibility": round(random.uniform(50, 95), 2),
                    "price_stability": round(random.uniform(50, 95), 2),
                    "return_signal": round(random.uniform(50, 95), 2),
                })
                rows.append((
                    now - timedelta(weeks=week),
                    str(product.id),
                    round(score, 2),
                    1,
                    components,
                ))

        with connection.cursor() as cursor:
            sql = """
                INSERT INTO "scoring"."dudscore_history"
                    (time, product_id, score, config_version, component_scores)
                VALUES (%s, %s, %s, %s, %s)
            """
            cursor.executemany(sql, rows)

        self.stdout.write(f"  DudScore History: {len(rows)}")

    # ── Discussions ───────────────────────────────────────────────

    def _seed_discussions(self, products):
        product_list = list(products.values())[:10]
        # Need a user for discussions
        user = User.objects.filter(email="test@whydud.com").first()
        if not user:
            user = User.objects.create_user(
                email="test@whydud.com",
                password="testpass123",
                name="Test User",
            )

        THREADS = [
            ("question", "Is the camera quality good for low light photography?",
             "I'm considering buying this but most reviews don't mention low light performance. Can anyone share real-world samples?"),
            ("experience", "My experience after 3 months of daily use",
             "I bought this 3 months ago and here's my detailed review. Overall very satisfied with the purchase. Battery easily lasts a full day with moderate to heavy usage."),
            ("tip", "Pro tip: How to get the best battery life",
             "After testing multiple settings, I found that turning off always-on display and setting refresh rate to adaptive saves about 20% battery. Also disable 5G when not needed."),
            ("question", "How does this compare to the previous model?",
             "Thinking of upgrading from last year's model. Is it worth the extra money or should I wait for the next version?"),
            ("alert", "Price dropped to all-time low on Amazon!",
             "Just noticed the price dropped to its lowest ever on Amazon India. Might be a pricing error so grab it quick if you've been waiting!"),
        ]

        count = 0
        for product in product_list:
            thread_data = random.choice(THREADS)
            thread = DiscussionThread.objects.create(
                product=product,
                user=user,
                thread_type=thread_data[0],
                title=thread_data[1],
                body=thread_data[2],
                upvotes=random.randint(5, 50),
                view_count=random.randint(50, 500),
            )

            # Add 1-3 replies
            replies_text = [
                "Thanks for sharing! This is really helpful.",
                "I had the same question. Can confirm the quality is great.",
                "Agree with this. I've been using it for 2 months and very happy.",
                "Not sure I agree. My experience has been different.",
                "Great tip! Saved me a lot of battery.",
            ]
            num_replies = random.randint(1, 3)
            for i in range(num_replies):
                DiscussionReply.objects.create(
                    thread=thread,
                    user=user,
                    body=random.choice(replies_text),
                    upvotes=random.randint(0, 20),
                )
            thread.reply_count = num_replies
            thread.last_reply_at = _dt(random.randint(0, 5))
            thread.save(update_fields=["reply_count", "last_reply_at"])
            count += 1

        self.stdout.write(f"  Discussion Threads: {count}")

    # ── Cities ────────────────────────────────────────────────────

    def _seed_cities(self):
        CITIES = [
            ("Mumbai", "Maharashtra", 9.50, 120, "high", 25.00, "hard"),
            ("Delhi", "Delhi", 8.00, 150, "low", 20.00, "hard"),
            ("Bangalore", "Karnataka", 7.50, 60, "medium", 30.00, "medium"),
            ("Chennai", "Tamil Nadu", 6.50, 200, "high", 22.00, "hard"),
            ("Hyderabad", "Telangana", 7.00, 180, "medium", 18.00, "medium"),
            ("Kolkata", "West Bengal", 8.50, 160, "high", 15.00, "soft"),
            ("Pune", "Maharashtra", 8.00, 90, "medium", 20.00, "medium"),
            ("Ahmedabad", "Gujarat", 6.00, 200, "low", 12.00, "hard"),
            ("Jaipur", "Rajasthan", 7.00, 210, "low", 10.00, "hard"),
            ("Lucknow", "Uttar Pradesh", 6.50, 170, "medium", 14.00, "medium"),
        ]
        for city, state, tariff, cool_days, humidity, water_tariff, hardness in CITIES:
            CityReferenceData.objects.update_or_create(
                city_name=city,
                state=state,
                defaults=dict(
                    electricity_tariff_residential=Decimal(str(tariff)),
                    cooling_days_per_year=cool_days,
                    humidity_level=humidity,
                    water_tariff_per_kl=Decimal(str(water_tariff)),
                    water_hardness=hardness,
                ),
            )
        self.stdout.write(f"  Cities: {len(CITIES)}")

    # ── TCO Models ────────────────────────────────────────────────

    def _seed_tco_models(self, categories):
        MODELS = [
            {
                "category_slug": "air-conditioners",
                "name": "Air Conditioner TCO (5-Year)",
                "input_schema": {
                    "fields": [
                        {"key": "purchase_price", "label": "Purchase Price (₹)", "type": "number"},
                        {"key": "tonnage", "label": "Tonnage", "type": "select", "options": [1.0, 1.5, 2.0]},
                        {"key": "star_rating", "label": "Star Rating", "type": "select", "options": [3, 4, 5]},
                        {"key": "hours_per_day", "label": "Daily Usage (hours)", "type": "number", "default": 8},
                        {"key": "ownership_years", "label": "Ownership (years)", "type": "number", "default": 5},
                    ],
                },
                "cost_components": {
                    "electricity": {"formula": "tonnage * 1.2 * hours_per_day * city.cooling_days * city.tariff * years", "label": "Electricity Cost"},
                    "maintenance": {"formula": "2000 * years", "label": "Annual Maintenance"},
                    "installation": {"flat": 3000, "label": "Installation"},
                },
            },
            {
                "category_slug": "refrigerators",
                "name": "Refrigerator TCO (7-Year)",
                "input_schema": {
                    "fields": [
                        {"key": "purchase_price", "label": "Purchase Price (₹)", "type": "number"},
                        {"key": "capacity", "label": "Capacity (L)", "type": "number"},
                        {"key": "star_rating", "label": "Star Rating", "type": "select", "options": [2, 3, 4, 5]},
                        {"key": "ownership_years", "label": "Ownership (years)", "type": "number", "default": 7},
                    ],
                },
                "cost_components": {
                    "electricity": {"formula": "annual_kwh * city.tariff * years", "label": "Electricity Cost"},
                    "maintenance": {"formula": "1500 * years", "label": "Annual Maintenance"},
                },
            },
            {
                "category_slug": "washing-machines",
                "name": "Washing Machine TCO (5-Year)",
                "input_schema": {
                    "fields": [
                        {"key": "purchase_price", "label": "Purchase Price (₹)", "type": "number"},
                        {"key": "capacity", "label": "Capacity (Kg)", "type": "number"},
                        {"key": "type", "label": "Type", "type": "select", "options": ["Front Load", "Top Load"]},
                        {"key": "loads_per_week", "label": "Loads per Week", "type": "number", "default": 4},
                        {"key": "ownership_years", "label": "Ownership (years)", "type": "number", "default": 5},
                    ],
                },
                "cost_components": {
                    "electricity": {"formula": "kwh_per_load * loads_per_week * 52 * city.tariff * years", "label": "Electricity Cost"},
                    "water": {"formula": "liters_per_load * loads_per_week * 52 * city.water_tariff * years / 1000", "label": "Water Cost"},
                    "detergent": {"formula": "50 * loads_per_week * 52 * years", "label": "Detergent Cost"},
                },
            },
        ]
        for m in MODELS:
            cat = categories.get(m["category_slug"])
            if not cat:
                continue
            TCOModel.objects.update_or_create(
                category=cat,
                version=1,
                defaults=dict(
                    name=m["name"],
                    is_active=True,
                    input_schema=m["input_schema"],
                    cost_components=m["cost_components"],
                ),
            )
        self.stdout.write(f"  TCO Models: {len(MODELS)}")

    # ── Gift Card Catalog ─────────────────────────────────────────

    def _seed_gift_card_catalog(self):
        CARDS = [
            ("Amazon", "amazon", "https://placehold.co/120x60/FF9900/fff?text=Amazon", [100, 250, 500, 1000, 2000], "shopping"),
            ("Flipkart", "flipkart", "https://placehold.co/120x60/2874F0/fff?text=Flipkart", [100, 250, 500, 1000, 2000], "shopping"),
            ("Swiggy", "swiggy", "https://placehold.co/120x60/FC8019/fff?text=Swiggy", [100, 200, 500], "food"),
            ("Zomato", "zomato", "https://placehold.co/120x60/E23744/fff?text=Zomato", [100, 200, 500], "food"),
            ("BookMyShow", "bookmyshow", "https://placehold.co/120x60/C4242B/fff?text=BMS", [200, 500, 1000], "entertainment"),
            ("Myntra", "myntra", "https://placehold.co/120x60/FF3F6C/fff?text=Myntra", [200, 500, 1000], "fashion"),
        ]
        for name, slug, logo, denoms, cat in CARDS:
            GiftCardCatalog.objects.update_or_create(
                brand_slug=slug,
                defaults=dict(
                    brand_name=name,
                    brand_logo_url=logo,
                    denominations=denoms,
                    category=cat,
                    is_active=True,
                    fulfillment_partner="woohoo",
                ),
            )
        self.stdout.write(f"  Gift Card Catalog: {len(CARDS)}")

    # ── Test User ─────────────────────────────────────────────────

    def _seed_test_user(self):
        user, created = User.objects.update_or_create(
            email="test@whydud.com",
            defaults=dict(
                name="Rahul Sharma",
                role="connected",
                subscription_tier="free",
                has_whydud_email=True,
                email_verified=True,
            ),
        )
        if created:
            user.set_password("testpass123")
            user.save()

        # @whyd.xyz email
        WhydudEmail.objects.update_or_create(
            user=user,
            defaults=dict(
                username="rahul",
                is_active=True,
                total_emails_received=47,
                total_orders_detected=12,
                onboarding_complete=True,
                marketplaces_registered=["amazon_in", "flipkart", "myntra", "croma"],
            ),
        )

        # Payment methods (card vault — NO card numbers)
        PAYMENT_METHODS = [
            ("credit_card", "HDFC Bank", "Regalia", "visa"),
            ("credit_card", "ICICI Bank", "Amazon Pay Credit Card", "visa"),
            ("debit_card", "SBI", "Platinum", "rupay"),
        ]
        PaymentMethod.objects.filter(user=user).delete()
        for method_type, bank, variant, network in PAYMENT_METHODS:
            PaymentMethod.objects.create(
                user=user,
                method_type=method_type,
                bank_name=bank,
                card_variant=variant,
                card_network=network,
                emi_eligible=method_type == "credit_card",
                nickname=f"{bank} {variant}",
            )

        self.stdout.write(f"  Test User: {user.email} (password: testpass123)")
        return user

    # ── Wishlists ─────────────────────────────────────────────────

    def _seed_wishlists(self, user, products):
        product_list = list(products.values())

        lists_data = [
            ("Birthday Gifts", True, True, "birthday-gifts"),
            ("Home Setup", False, False, None),
            ("Tech Wishlist", False, True, "tech-wishlist"),
        ]
        for name, is_default, is_public, share_slug in lists_data:
            wl, _ = Wishlist.objects.update_or_create(
                user=user,
                name=name,
                defaults=dict(is_default=is_default, is_public=is_public, share_slug=share_slug),
            )
            # Add 2-3 random products
            items = random.sample(product_list, min(3, len(product_list)))
            for p in items:
                WishlistItem.objects.update_or_create(
                    wishlist=wl,
                    product=p,
                    defaults=dict(
                        price_when_added=p.current_best_price,
                        target_price=(p.current_best_price * Decimal("0.85")).quantize(Decimal("1.00")) if p.current_best_price else None,
                        alert_enabled=True,
                        current_price=p.current_best_price,
                        price_change_pct=Decimal(str(round(random.uniform(-10, 5), 2))),
                    ),
                )
        self.stdout.write("  Wishlists: 3 (with items)")

    # ── Rewards ───────────────────────────────────────────────────

    def _seed_rewards(self, user):
        RewardBalance.objects.update_or_create(
            user=user,
            defaults=dict(
                total_earned=450,
                total_spent=0,
                total_expired=0,
                current_balance=450,
            ),
        )

        LEDGER = [
            (50, "email_connect", "Connected @whyd.xyz email", 14),
            (20, "review", "Wrote a review for Samsung Galaxy S24 FE", 10),
            (20, "review", "Wrote a review for boAt Airdopes 141", 8),
            (30, "referral", "Referred a friend (Priya)", 5),
            (20, "review", "Wrote a review for HP Pavilion 15", 3),
            (10, "login_streak", "7-day login streak bonus", 2),
            (20, "review", "Wrote a review for Prestige Iris Mixer", 1),
        ]
        RewardPointsLedger.objects.filter(user=user).delete()
        for points, action, desc, days_ago in LEDGER:
            RewardPointsLedger.objects.create(
                user=user,
                points=points,
                action_type=action,
                description=desc,
            )
        self.stdout.write("  Rewards: Balance 450 + 7 ledger entries")

    # ── Inbox Emails ──────────────────────────────────────────────

    def _seed_inbox(self, user, products):
        EMAILS = [
            {
                "sender": "auto-confirm@amazon.in",
                "sender_name": "Amazon.in",
                "subject": "Your Amazon.in order #402-1234567-8901234",
                "category": "order",
                "marketplace": "amazon_in",
                "days_ago": 2,
                "is_read": True,
            },
            {
                "sender": "noreply@flipkart.com",
                "sender_name": "Flipkart",
                "subject": "Your Flipkart order OD123456789 has been shipped!",
                "category": "shipping",
                "marketplace": "flipkart",
                "days_ago": 3,
                "is_read": True,
            },
            {
                "sender": "refunds@myntra.com",
                "sender_name": "Myntra",
                "subject": "Refund of ₹2,499 processed for order #MYN-9876543",
                "category": "refund",
                "marketplace": "myntra",
                "days_ago": 5,
                "is_read": False,
            },
            {
                "sender": "support@croma.com",
                "sender_name": "Croma",
                "subject": "Return window closing: 3 days left for order #CRM-456789",
                "category": "return",
                "marketplace": "croma",
                "days_ago": 1,
                "is_read": False,
            },
            {
                "sender": "noreply@swiggy.in",
                "sender_name": "Swiggy",
                "subject": "Your Swiggy One membership renews on March 15",
                "category": "subscription",
                "marketplace": "swiggy",
                "days_ago": 7,
                "is_read": True,
            },
            {
                "sender": "offers@amazon.in",
                "sender_name": "Amazon.in",
                "subject": "Great Indian Festival: Up to 70% off on Electronics",
                "category": "promo",
                "marketplace": "amazon_in",
                "days_ago": 4,
                "is_read": False,
            },
            {
                "sender": "auto-confirm@amazon.in",
                "sender_name": "Amazon.in",
                "subject": "Your Amazon.in order #402-9876543-2109876 delivered!",
                "category": "order",
                "marketplace": "amazon_in",
                "days_ago": 10,
                "is_read": True,
            },
        ]

        whydud_email = WhydudEmail.objects.filter(user=user).first()
        InboxEmail.objects.filter(user=user).delete()

        for e in EMAILS:
            InboxEmail.objects.create(
                user=user,
                whydud_email=whydud_email,
                message_id=f"<{uuid.uuid4().hex}@whydud.mail>",
                sender_address=e["sender"],
                sender_name=e["sender_name"],
                subject=e["subject"],
                received_at=_dt(e["days_ago"]),
                category=e["category"],
                marketplace=e["marketplace"],
                confidence=Decimal("0.95"),
                parse_status="parsed",
                parsed_entity_type="order" if e["category"] in ("order", "shipping") else "",
                is_read=e["is_read"],
                raw_size_bytes=random.randint(5000, 50000),
            )

        # Seed some parsed orders
        product_list = list(products.values())[:5]
        ParsedOrder.objects.filter(user=user).delete()
        for i, p in enumerate(product_list):
            ParsedOrder.objects.create(
                user=user,
                source="whydud_email",
                order_id=f"ORD-{random.randint(100000, 999999)}",
                email_message_id=f"<order-{uuid.uuid4().hex[:12]}@whydud.mail>",
                marketplace="amazon_in" if i % 2 == 0 else "flipkart",
                product_name=p.title,
                quantity=1,
                price_paid=p.current_best_price or _rand_paisa(1000, 50000),
                tax=(p.current_best_price * Decimal("0.18")).quantize(Decimal("1.00")) if p.current_best_price else _rand_paisa(100, 5000),
                shipping_cost=Decimal("0.00"),
                total_amount=p.current_best_price if p.current_best_price else _rand_paisa(1000, 50000),
                order_date=(_dt(random.randint(5, 60))).date(),
                delivery_date=(_dt(random.randint(1, 10))).date(),
                seller_name="Appario Retail" if i % 2 == 0 else "RetailNet",
                payment_method="HDFC Regalia Credit Card",
                matched_product=p,
                match_confidence=Decimal("0.95"),
                match_status="matched",
            )

        # A refund
        order = ParsedOrder.objects.filter(user=user).first()
        if order:
            RefundTracking.objects.create(
                user=user,
                order=order,
                status="processing",
                refund_amount=order.price_paid,
                initiated_at=_dt(3),
                expected_by=_dt(-4),
                marketplace="amazon_in",
                delay_days=0,
            )

        # A return window
        order2 = ParsedOrder.objects.filter(user=user).last()
        if order2:
            ReturnWindow.objects.create(
                user=user,
                order=order2,
                window_end_date=date.today() + timedelta(days=5),
            )

        # Subscriptions
        DetectedSubscription.objects.filter(user=user).delete()
        SUBS = [
            ("Amazon Prime", 1499, "yearly"),
            ("Swiggy One", 299, "monthly"),
            ("YouTube Premium", 129, "monthly"),
        ]
        for name, amount, cycle in SUBS:
            DetectedSubscription.objects.create(
                user=user,
                service_name=name,
                amount=Decimal(str(amount * 100)),  # paisa
                billing_cycle=cycle,
                next_renewal=date.today() + timedelta(days=random.randint(10, 60)),
                is_active=True,
            )

        self.stdout.write(f"  Inbox: {len(EMAILS)} emails, {len(product_list)} orders, 1 refund, 1 return, {len(SUBS)} subscriptions")
