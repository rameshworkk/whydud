"""
Seed CategoryPreferenceSchema records for 7 product categories.

Creates missing categories (air-purifiers, water-purifiers, vehicles)
and populates JSONB schemas matching the frontend PreferenceSection[] shape.

Usage:
    python manage.py seed_preference_schemas
    python manage.py seed_preference_schemas --flush   # Delete existing and re-seed
"""

from django.core.management.base import BaseCommand

from apps.products.models import Category, CategoryPreferenceSchema


# ═══════════════════════════════════════════════════════════════════════════════
# 1. Air Purifiers — per ARCHITECTURE.md Epic 8 US-8.1 (verbatim)
# ═══════════════════════════════════════════════════════════════════════════════

AIR_PURIFIERS_SCHEMA = {
    "sections": [
        {
            "key": "room_requirements",
            "title": "Room Requirements",
            "icon": "home",
            "fields": [
                {
                    "key": "room_size",
                    "type": "number",
                    "label": "Room Size",
                    "unit": "sq ft",
                    "min": 50,
                    "max": 2000,
                    "defaultValue": 200,
                    "quickSelect": [
                        {"label": "Small (< 150 sq ft)", "value": 120},
                        {"label": "Medium (150–300 sq ft)", "value": 250},
                        {"label": "Large (> 300 sq ft)", "value": 500},
                    ],
                },
                {
                    "key": "room_type",
                    "type": "dropdown",
                    "label": "Room Type",
                    "options": [
                        "Bedroom",
                        "Living Room",
                        "Office",
                        "Kitchen",
                        "Nursery",
                        "Basement",
                    ],
                    "defaultValue": "Bedroom",
                },
                {
                    "key": "ceiling_height",
                    "type": "dropdown",
                    "label": "Ceiling Height",
                    "options": [
                        "Standard (8–9 ft)",
                        "High (10–12 ft)",
                        "Very High (> 12 ft)",
                    ],
                    "defaultValue": "Standard (8–9 ft)",
                },
            ],
        },
        {
            "key": "health_sensitivity",
            "title": "Health & Sensitivity",
            "icon": "heart",
            "fields": [
                {
                    "key": "allergy_level",
                    "type": "radio",
                    "label": "Allergy Level",
                    "options": ["Normal", "Sensitive", "Highly Sensitive"],
                    "defaultValue": "Normal",
                },
                {
                    "key": "concern_tags",
                    "type": "tags",
                    "label": "Primary Concerns",
                    "options": [
                        "Dust",
                        "Pollen",
                        "Smoke",
                        "Odor",
                        "Pet Hair",
                        "PM2.5 Pollution",
                    ],
                },
            ],
        },
        {
            "key": "filtration",
            "title": "Filtration Preferences",
            "icon": "filter",
            "fields": [
                {
                    "key": "hepa_level",
                    "type": "dropdown",
                    "label": "Minimum HEPA Level",
                    "options": [
                        "HEPA H11",
                        "HEPA H12",
                        "HEPA H13 (True HEPA)",
                        "HEPA H14 (Medical Grade)",
                    ],
                    "defaultValue": "HEPA H13 (True HEPA)",
                },
                {
                    "key": "activated_carbon",
                    "type": "toggle",
                    "label": "Activated Carbon Filter",
                    "defaultValue": False,
                },
                {
                    "key": "uv_c",
                    "type": "toggle",
                    "label": "UV-C Sterilization",
                    "defaultValue": False,
                },
                {
                    "key": "ionizer",
                    "type": "toggle",
                    "label": "Ionizer",
                    "defaultValue": False,
                },
                {
                    "key": "ozone_free",
                    "type": "toggle",
                    "label": "Ozone-Free Certification",
                    "defaultValue": True,
                },
            ],
        },
        {
            "key": "performance",
            "title": "Performance",
            "icon": "zap",
            "fields": [
                {
                    "key": "cadr_requirement",
                    "type": "slider",
                    "label": "CADR Requirement",
                    "unit": "m\u00b3/hr",
                    "min": 50,
                    "max": 800,
                    "defaultValue": 200,
                },
                {
                    "key": "auto_sensing",
                    "type": "toggle",
                    "label": "Auto-sensing / AQI Display",
                    "defaultValue": False,
                },
                {
                    "key": "noise_tolerance",
                    "type": "radio",
                    "label": "Noise Tolerance",
                    "options": [
                        "Ultra Quiet (< 30 dB)",
                        "Moderate (< 50 dB)",
                        "Any",
                    ],
                    "defaultValue": "Moderate (< 50 dB)",
                },
            ],
        },
        {
            "key": "smart_features",
            "title": "Smart Features",
            "icon": "smartphone",
            "fields": [
                {
                    "key": "app_support",
                    "type": "toggle",
                    "label": "App Control Support",
                    "defaultValue": False,
                },
                {
                    "key": "voice_assistant",
                    "type": "tags",
                    "label": "Voice Assistant Compatibility",
                    "options": ["Alexa", "Google Home", "Apple HomeKit"],
                },
                {
                    "key": "timer_scheduling",
                    "type": "toggle",
                    "label": "Timer & Scheduling",
                    "defaultValue": False,
                },
            ],
        },
        {
            "key": "cost",
            "title": "Cost Preferences",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 3000,
                    "max": 80000,
                    "defaultValue": [5000, 25000],
                },
                {
                    "key": "filter_cost_limit",
                    "type": "slider",
                    "label": "Filter Replacement Cost Limit",
                    "unit": "\u20b9",
                    "min": 500,
                    "max": 10000,
                    "defaultValue": 3000,
                },
                {
                    "key": "filter_lifespan",
                    "type": "dropdown",
                    "label": "Minimum Filter Lifespan",
                    "options": [
                        "3 months",
                        "6 months",
                        "12 months",
                        "18+ months",
                    ],
                    "defaultValue": "6 months",
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 2. Air Conditioners — per US-8.2
# ═══════════════════════════════════════════════════════════════════════════════

ACS_SCHEMA = {
    "sections": [
        {
            "key": "room",
            "title": "Room Details",
            "icon": "home",
            "fields": [
                {
                    "key": "room_size",
                    "type": "number",
                    "label": "Room Size",
                    "unit": "sq ft",
                    "min": 50,
                    "max": 3000,
                    "defaultValue": 150,
                    "quickSelect": [
                        {"label": "Small (< 120 sq ft)", "value": 100},
                        {"label": "Medium (120–200 sq ft)", "value": 160},
                        {"label": "Large (> 200 sq ft)", "value": 300},
                    ],
                },
                {
                    "key": "floor",
                    "type": "dropdown",
                    "label": "Floor Level",
                    "options": [
                        "Ground Floor",
                        "1st–3rd Floor",
                        "4th+ Floor",
                        "Top Floor / Direct Sunlight",
                    ],
                    "defaultValue": "1st–3rd Floor",
                },
            ],
        },
        {
            "key": "type_tonnage",
            "title": "Type & Tonnage",
            "icon": "wind",
            "fields": [
                {
                    "key": "ac_type",
                    "type": "radio",
                    "label": "AC Type",
                    "options": ["Split", "Window", "Portable", "No Preference"],
                    "defaultValue": "Split",
                },
                {
                    "key": "tonnage",
                    "type": "dropdown",
                    "label": "Tonnage",
                    "options": [
                        "0.8 Ton (small room)",
                        "1.0 Ton",
                        "1.5 Ton (most common)",
                        "2.0 Ton (large room)",
                    ],
                    "defaultValue": "1.5 Ton (most common)",
                },
                {
                    "key": "inverter",
                    "type": "toggle",
                    "label": "Inverter Compressor Required",
                    "defaultValue": True,
                },
            ],
        },
        {
            "key": "energy",
            "title": "Energy Efficiency",
            "icon": "leaf",
            "fields": [
                {
                    "key": "star_rating",
                    "type": "radio",
                    "label": "Minimum Star Rating",
                    "options": ["3 Star", "4 Star", "5 Star", "No Preference"],
                    "defaultValue": "3 Star",
                },
                {
                    "key": "installation_type",
                    "type": "dropdown",
                    "label": "Installation Type",
                    "options": [
                        "Standard (copper piping)",
                        "High-rise (extended piping)",
                        "Not Sure",
                    ],
                    "defaultValue": "Standard (copper piping)",
                },
            ],
        },
        {
            "key": "smart_features",
            "title": "Smart Features",
            "icon": "smartphone",
            "fields": [
                {
                    "key": "wifi_control",
                    "type": "toggle",
                    "label": "Wi-Fi / App Control",
                    "defaultValue": False,
                },
                {
                    "key": "voice_assistant",
                    "type": "tags",
                    "label": "Voice Assistant",
                    "options": ["Alexa", "Google Home"],
                },
                {
                    "key": "noise_tolerance",
                    "type": "radio",
                    "label": "Noise Tolerance",
                    "options": [
                        "Silent (< 30 dB)",
                        "Moderate (< 45 dB)",
                        "Any",
                    ],
                    "defaultValue": "Moderate (< 45 dB)",
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 15000,
                    "max": 120000,
                    "defaultValue": [25000, 50000],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 3. Water Purifiers — per US-8.3
# ═══════════════════════════════════════════════════════════════════════════════

WATER_PURIFIERS_SCHEMA = {
    "sections": [
        {
            "key": "water_source",
            "title": "Water Source",
            "icon": "droplets",
            "fields": [
                {
                    "key": "source_type",
                    "type": "radio",
                    "label": "Primary Water Source",
                    "options": [
                        "Municipality / Corporation",
                        "Borewell / Groundwater",
                        "Mixed / Tanker",
                    ],
                    "defaultValue": "Municipality / Corporation",
                },
                {
                    "key": "tds_level",
                    "type": "dropdown",
                    "label": "Approximate TDS Level",
                    "options": [
                        "Low (< 200 ppm)",
                        "Medium (200–500 ppm)",
                        "High (500–1000 ppm)",
                        "Very High (> 1000 ppm)",
                        "Not Sure",
                    ],
                    "defaultValue": "Not Sure",
                },
            ],
        },
        {
            "key": "purification",
            "title": "Purification Technology",
            "icon": "shield-check",
            "fields": [
                {
                    "key": "purification_type",
                    "type": "tags",
                    "label": "Purification Method",
                    "options": ["RO", "UV", "UF", "RO+UV", "RO+UV+UF"],
                },
                {
                    "key": "mineral_retention",
                    "type": "toggle",
                    "label": "Mineral Retention (TDS Controller)",
                    "defaultValue": True,
                },
                {
                    "key": "hot_water",
                    "type": "toggle",
                    "label": "Hot Water Dispenser",
                    "defaultValue": False,
                },
            ],
        },
        {
            "key": "capacity",
            "title": "Capacity & Usage",
            "icon": "gauge",
            "fields": [
                {
                    "key": "daily_consumption",
                    "type": "slider",
                    "label": "Daily Water Consumption",
                    "unit": "litres",
                    "min": 2,
                    "max": 30,
                    "defaultValue": 8,
                },
                {
                    "key": "storage_capacity",
                    "type": "dropdown",
                    "label": "Storage Tank Capacity",
                    "options": [
                        "No Tank (direct flow)",
                        "5–7 litres",
                        "8–10 litres",
                        "12+ litres",
                    ],
                    "defaultValue": "8–10 litres",
                },
                {
                    "key": "family_size",
                    "type": "dropdown",
                    "label": "Family Size",
                    "options": [
                        "1–2 members",
                        "3–4 members",
                        "5–6 members",
                        "7+ members",
                    ],
                    "defaultValue": "3–4 members",
                },
            ],
        },
        {
            "key": "smart_features",
            "title": "Smart Features",
            "icon": "smartphone",
            "fields": [
                {
                    "key": "filter_alert",
                    "type": "toggle",
                    "label": "Filter Change Alert / Indicator",
                    "defaultValue": True,
                },
                {
                    "key": "tds_display",
                    "type": "toggle",
                    "label": "Real-time TDS Display",
                    "defaultValue": False,
                },
                {
                    "key": "auto_shutoff",
                    "type": "toggle",
                    "label": "Auto Shut-off When Tank Full",
                    "defaultValue": True,
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 3000,
                    "max": 50000,
                    "defaultValue": [8000, 20000],
                },
                {
                    "key": "cartridge_cost_limit",
                    "type": "slider",
                    "label": "Annual Cartridge/Filter Cost Limit",
                    "unit": "\u20b9",
                    "min": 500,
                    "max": 8000,
                    "defaultValue": 3000,
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 4. Refrigerators — per US-8.4
# ═══════════════════════════════════════════════════════════════════════════════

REFRIGERATORS_SCHEMA = {
    "sections": [
        {
            "key": "capacity",
            "title": "Capacity",
            "icon": "ruler",
            "fields": [
                {
                    "key": "capacity_litres",
                    "type": "slider",
                    "label": "Capacity",
                    "unit": "litres",
                    "min": 50,
                    "max": 700,
                    "defaultValue": 260,
                    "quickSelect": [
                        {"label": "Single (< 200L)", "value": 180},
                        {"label": "Family (200–400L)", "value": 300},
                        {"label": "Large (> 400L)", "value": 500},
                    ],
                },
                {
                    "key": "family_size",
                    "type": "dropdown",
                    "label": "Family Size",
                    "options": [
                        "1–2 members",
                        "3–4 members",
                        "5–6 members",
                        "7+ members",
                    ],
                    "defaultValue": "3–4 members",
                },
            ],
        },
        {
            "key": "type",
            "title": "Refrigerator Type",
            "icon": "box",
            "fields": [
                {
                    "key": "door_type",
                    "type": "radio",
                    "label": "Door Type",
                    "options": [
                        "Single Door",
                        "Double Door",
                        "Side-by-Side",
                        "French Door",
                        "Triple Door",
                        "No Preference",
                    ],
                    "defaultValue": "Double Door",
                },
                {
                    "key": "frost_free",
                    "type": "toggle",
                    "label": "Frost-Free Required",
                    "defaultValue": True,
                },
            ],
        },
        {
            "key": "energy",
            "title": "Energy Efficiency",
            "icon": "leaf",
            "fields": [
                {
                    "key": "star_rating",
                    "type": "radio",
                    "label": "Minimum Star Rating",
                    "options": ["2 Star", "3 Star", "4 Star", "5 Star", "No Preference"],
                    "defaultValue": "3 Star",
                },
                {
                    "key": "inverter",
                    "type": "toggle",
                    "label": "Inverter Compressor",
                    "defaultValue": True,
                },
            ],
        },
        {
            "key": "features",
            "title": "Features",
            "icon": "settings",
            "fields": [
                {
                    "key": "convertible",
                    "type": "toggle",
                    "label": "Convertible (Fridge \u2194 Freezer)",
                    "defaultValue": False,
                },
                {
                    "key": "water_dispenser",
                    "type": "toggle",
                    "label": "Water / Ice Dispenser",
                    "defaultValue": False,
                },
                {
                    "key": "wifi_control",
                    "type": "toggle",
                    "label": "Wi-Fi / Smart Features",
                    "defaultValue": False,
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 8000,
                    "max": 200000,
                    "defaultValue": [15000, 45000],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 5. Washing Machines — per US-8.5
# ═══════════════════════════════════════════════════════════════════════════════

WASHING_MACHINES_SCHEMA = {
    "sections": [
        {
            "key": "capacity",
            "title": "Capacity",
            "icon": "ruler",
            "fields": [
                {
                    "key": "capacity_kg",
                    "type": "slider",
                    "label": "Wash Capacity",
                    "unit": "kg",
                    "min": 5,
                    "max": 12,
                    "defaultValue": 7,
                    "quickSelect": [
                        {"label": "Small (5–6 kg)", "value": 6},
                        {"label": "Medium (7–8 kg)", "value": 7},
                        {"label": "Large (9+ kg)", "value": 9},
                    ],
                },
                {
                    "key": "family_size",
                    "type": "dropdown",
                    "label": "Family Size",
                    "options": [
                        "1–2 members",
                        "3–4 members",
                        "5–6 members",
                        "7+ members",
                    ],
                    "defaultValue": "3–4 members",
                },
            ],
        },
        {
            "key": "type",
            "title": "Machine Type",
            "icon": "box",
            "fields": [
                {
                    "key": "loading_type",
                    "type": "radio",
                    "label": "Loading Type",
                    "options": ["Top Load", "Front Load", "No Preference"],
                    "defaultValue": "Top Load",
                },
                {
                    "key": "inverter",
                    "type": "toggle",
                    "label": "Inverter Motor",
                    "defaultValue": True,
                },
                {
                    "key": "build_type",
                    "type": "radio",
                    "label": "Build Type",
                    "options": [
                        "Fully Automatic",
                        "Semi Automatic",
                        "No Preference",
                    ],
                    "defaultValue": "Fully Automatic",
                },
            ],
        },
        {
            "key": "programs",
            "title": "Wash Programs",
            "icon": "list",
            "fields": [
                {
                    "key": "required_programs",
                    "type": "tags",
                    "label": "Must-Have Programs",
                    "options": [
                        "Quick Wash (15 min)",
                        "Delicate / Wool",
                        "Heavy Duty",
                        "Steam Wash",
                        "Hot Water Wash",
                        "Drum Clean",
                        "Soak",
                    ],
                },
                {
                    "key": "dryer",
                    "type": "radio",
                    "label": "Built-in Dryer",
                    "options": [
                        "Yes (Washer-Dryer)",
                        "No (Wash Only)",
                        "No Preference",
                    ],
                    "defaultValue": "No (Wash Only)",
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 6000,
                    "max": 80000,
                    "defaultValue": [12000, 30000],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 6. Vehicles — per US-8.6
# ═══════════════════════════════════════════════════════════════════════════════

VEHICLES_SCHEMA = {
    "sections": [
        {
            "key": "vehicle_type",
            "title": "Vehicle Type",
            "icon": "car",
            "fields": [
                {
                    "key": "type",
                    "type": "radio",
                    "label": "Vehicle Type",
                    "options": ["Car", "Bike", "Scooter", "SUV"],
                    "defaultValue": "Car",
                },
                {
                    "key": "body_type",
                    "type": "dropdown",
                    "label": "Body Type (Cars/SUVs)",
                    "options": [
                        "Hatchback",
                        "Sedan",
                        "Compact SUV",
                        "Mid-size SUV",
                        "Full-size SUV",
                        "MPV / MUV",
                        "Not Applicable",
                    ],
                    "defaultValue": "Compact SUV",
                },
                {
                    "key": "passengers",
                    "type": "dropdown",
                    "label": "Seating Capacity",
                    "options": ["2", "4–5", "6–7", "8+", "Not Applicable"],
                    "defaultValue": "4–5",
                },
            ],
        },
        {
            "key": "fuel",
            "title": "Fuel & Powertrain",
            "icon": "fuel",
            "fields": [
                {
                    "key": "fuel_type",
                    "type": "tags",
                    "label": "Fuel Type",
                    "options": [
                        "Petrol",
                        "Diesel",
                        "Electric (EV)",
                        "Hybrid",
                        "CNG",
                    ],
                },
                {
                    "key": "transmission",
                    "type": "radio",
                    "label": "Transmission",
                    "options": ["Manual", "Automatic", "No Preference"],
                    "defaultValue": "No Preference",
                },
            ],
        },
        {
            "key": "use_case",
            "title": "Use Case",
            "icon": "map-pin",
            "fields": [
                {
                    "key": "primary_use",
                    "type": "radio",
                    "label": "Primary Usage",
                    "options": [
                        "City Commute",
                        "Highway / Long Distance",
                        "Both City & Highway",
                        "Off-road / Adventure",
                    ],
                    "defaultValue": "Both City & Highway",
                },
                {
                    "key": "daily_distance",
                    "type": "dropdown",
                    "label": "Average Daily Distance",
                    "options": [
                        "< 20 km",
                        "20–50 km",
                        "50–100 km",
                        "> 100 km",
                    ],
                    "defaultValue": "20–50 km",
                },
            ],
        },
        {
            "key": "features",
            "title": "Features",
            "icon": "settings",
            "fields": [
                {
                    "key": "required_features",
                    "type": "tags",
                    "label": "Must-Have Features",
                    "options": [
                        "Sunroof",
                        "Touchscreen Infotainment",
                        "Apple CarPlay / Android Auto",
                        "ADAS / Safety Suite",
                        "Cruise Control",
                        "360\u00b0 Camera",
                        "Ventilated Seats",
                        "Connected Car Tech",
                    ],
                },
                {
                    "key": "ground_clearance",
                    "type": "radio",
                    "label": "Ground Clearance Preference",
                    "options": [
                        "Low (sedan)",
                        "Medium (crossover)",
                        "High (SUV / off-road)",
                        "No Preference",
                    ],
                    "defaultValue": "No Preference",
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "On-road Budget Range",
                    "unit": "\u20b9",
                    "min": 50000,
                    "max": 5000000,
                    "defaultValue": [500000, 1500000],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# 7. Laptops — per US-8.7
# ═══════════════════════════════════════════════════════════════════════════════

LAPTOPS_SCHEMA = {
    "sections": [
        {
            "key": "use_case",
            "title": "Use Case",
            "icon": "briefcase",
            "fields": [
                {
                    "key": "primary_use",
                    "type": "radio",
                    "label": "Primary Use",
                    "options": [
                        "Web Browsing / Casual",
                        "Office / Productivity",
                        "Coding / Development",
                        "Gaming",
                        "Video Editing / Creative",
                        "Student / Education",
                    ],
                    "defaultValue": "Office / Productivity",
                },
                {
                    "key": "portability",
                    "type": "radio",
                    "label": "Portability Priority",
                    "options": [
                        "Ultra-portable (< 1.5 kg)",
                        "Balanced (1.5–2 kg)",
                        "Performance first (weight doesn't matter)",
                    ],
                    "defaultValue": "Balanced (1.5–2 kg)",
                },
            ],
        },
        {
            "key": "screen",
            "title": "Display",
            "icon": "monitor",
            "fields": [
                {
                    "key": "screen_size",
                    "type": "dropdown",
                    "label": "Screen Size",
                    "options": [
                        '13" (compact)',
                        '14" (most popular)',
                        '15.6" (standard)',
                        '16" (large)',
                        '17"+ (desktop replacement)',
                    ],
                    "defaultValue": '14" (most popular)',
                },
                {
                    "key": "resolution",
                    "type": "dropdown",
                    "label": "Minimum Resolution",
                    "options": [
                        "Full HD (1920\u00d71080)",
                        "2K / QHD (2560\u00d71440)",
                        "4K UHD",
                        "No Preference",
                    ],
                    "defaultValue": "Full HD (1920\u00d71080)",
                },
                {
                    "key": "refresh_rate",
                    "type": "dropdown",
                    "label": "Refresh Rate",
                    "options": [
                        "60 Hz (standard)",
                        "120 Hz (smooth)",
                        "144 Hz+ (gaming)",
                        "No Preference",
                    ],
                    "defaultValue": "60 Hz (standard)",
                },
                {
                    "key": "touchscreen",
                    "type": "toggle",
                    "label": "Touchscreen Required",
                    "defaultValue": False,
                },
            ],
        },
        {
            "key": "ram_storage",
            "title": "RAM & Storage",
            "icon": "cpu",
            "fields": [
                {
                    "key": "ram",
                    "type": "dropdown",
                    "label": "Minimum RAM",
                    "options": ["4 GB", "8 GB", "16 GB", "32 GB", "64 GB"],
                    "defaultValue": "8 GB",
                },
                {
                    "key": "storage_type",
                    "type": "radio",
                    "label": "Storage Type",
                    "options": ["SSD Only", "SSD + HDD", "No Preference"],
                    "defaultValue": "SSD Only",
                },
                {
                    "key": "storage_size",
                    "type": "dropdown",
                    "label": "Minimum Storage",
                    "options": ["256 GB", "512 GB", "1 TB", "2 TB"],
                    "defaultValue": "512 GB",
                },
            ],
        },
        {
            "key": "gpu",
            "title": "Graphics",
            "icon": "monitor",
            "fields": [
                {
                    "key": "gpu_required",
                    "type": "radio",
                    "label": "Dedicated GPU",
                    "options": [
                        "Not Needed (integrated is fine)",
                        "Entry-level (casual gaming / light editing)",
                        "Mid-range (serious gaming / video editing)",
                        "High-end (3D rendering / AAA gaming)",
                    ],
                    "defaultValue": "Not Needed (integrated is fine)",
                },
                {
                    "key": "brand_preference",
                    "type": "tags",
                    "label": "Preferred Laptop Brand",
                    "options": [
                        "Apple",
                        "Dell",
                        "HP",
                        "Lenovo",
                        "ASUS",
                        "Acer",
                        "MSI",
                        "Samsung",
                    ],
                },
            ],
        },
        {
            "key": "budget",
            "title": "Budget",
            "icon": "indian-rupee",
            "fields": [
                {
                    "key": "budget_range",
                    "type": "range_slider",
                    "label": "Budget Range",
                    "unit": "\u20b9",
                    "min": 20000,
                    "max": 300000,
                    "defaultValue": [40000, 80000],
                },
            ],
        },
    ],
}


# ═══════════════════════════════════════════════════════════════════════════════
# Category → schema mapping
# ═══════════════════════════════════════════════════════════════════════════════

# (category_slug, category_name, parent_slug, level, has_tco, schema_dict)
SCHEMAS = [
    ("air-purifiers", "Air Purifiers", "appliances", 2, False, AIR_PURIFIERS_SCHEMA),
    ("air-conditioners", "Air Conditioners", "appliances", 2, True, ACS_SCHEMA),
    ("water-purifiers", "Water Purifiers", "appliances", 2, False, WATER_PURIFIERS_SCHEMA),
    ("refrigerators", "Refrigerators", "appliances", 2, True, REFRIGERATORS_SCHEMA),
    ("washing-machines", "Washing Machines", "appliances", 2, True, WASHING_MACHINES_SCHEMA),
    ("vehicles", "Vehicles", None, 0, True, VEHICLES_SCHEMA),
    ("laptops", "Laptops", "electronics", 1, False, LAPTOPS_SCHEMA),
]


# ═══════════════════════════════════════════════════════════════════════════════
# Management command
# ═══════════════════════════════════════════════════════════════════════════════


class Command(BaseCommand):
    help = "Seed CategoryPreferenceSchema records for 7 product categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete existing CategoryPreferenceSchema records before seeding",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            deleted, _ = CategoryPreferenceSchema.objects.all().delete()
            self.stdout.write(f"  Flushed {deleted} existing schema(s)")

        created_count = 0
        updated_count = 0

        for slug, name, parent_slug, level, has_tco, schema_dict in SCHEMAS:
            # Ensure parent category exists
            parent = None
            if parent_slug:
                parent, _ = Category.objects.get_or_create(
                    slug=parent_slug,
                    defaults={"name": parent_slug.replace("-", " ").title(), "level": max(0, level - 1)},
                )

            # Ensure category exists
            category, cat_created = Category.objects.get_or_create(
                slug=slug,
                defaults={
                    "name": name,
                    "parent": parent,
                    "level": level,
                    "has_tco_model": has_tco,
                },
            )
            if cat_created:
                self.stdout.write(f"  Created category: {name} ({slug})")

            # Upsert the preference schema
            schema_obj, schema_created = CategoryPreferenceSchema.objects.update_or_create(
                category=category,
                defaults={
                    "schema": schema_dict,
                    "version": 1,
                    "is_active": True,
                },
            )

            if schema_created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + {name}: {len(schema_dict['sections'])} sections"))
            else:
                updated_count += 1
                self.stdout.write(f"  ~ {name}: updated ({len(schema_dict['sections'])} sections)")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. Created {created_count}, updated {updated_count} preference schema(s)."
            )
        )
