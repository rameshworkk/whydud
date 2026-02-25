"""Seed TCOModel records for 5 appliance categories.

Run:  python manage.py seed_tco_models
      python manage.py seed_tco_models --flush   (delete + re-seed)

Creates TCOModel records for:
  1. Air Conditioner (Split)
  2. Air Purifier
  3. Water Purifier
  4. Refrigerator
  5. Washing Machine

Units convention
~~~~~~~~~~~~~~~~
- ALL monetary default_value / min / max are in **paisa** (₹1 = 100 paisa),
  consistent with ``product.current_best_price`` stored in the DB.
- Electricity & water tariffs (``electricity_price``, ``water_price_per_kl``)
  are in **rupees** to match ``CityReferenceData`` fields. Formulas multiply
  by 100 to convert to paisa.
- Formulas always produce **paisa** output so ``formatPrice()`` works correctly.
"""

from django.core.management.base import BaseCommand

from apps.products.models import Category
from apps.tco.models import TCOModel

# ---------------------------------------------------------------------------
# Shared ownership-years config
# ---------------------------------------------------------------------------

OWNERSHIP_YEARS_DEFAULT = {"min": 1, "max": 10, "default": 5}
OWNERSHIP_YEARS_LONG = {"min": 1, "max": 15, "default": 7}

# ---------------------------------------------------------------------------
# 1. Air Conditioner (Split)
#    Typical 1.5T inverter split AC in India
# ---------------------------------------------------------------------------

AC_INPUT_SCHEMA = {
    "inputs": [
        {
            "key": "purchase_price",
            "label": "Purchase Price",
            "type": "currency",
            "unit": "\u20b9",
            "min": 1500000,
            "max": 20000000,
            "default_value": 3500000,
            "default_from": "product.current_best_price",
        },
        {
            "key": "resale_value",
            "label": "Expected Resale Value",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 10000000,
            "default_value": 500000,
        },
        {
            "key": "annual_energy_kwh",
            "label": "Annual Energy Usage",
            "type": "number",
            "unit": "kWh/year",
            "min": 400,
            "max": 3000,
            "default_value": 1200,
        },
        {
            "key": "electricity_price",
            "label": "Electricity Price",
            "type": "decimal",
            "unit": "\u20b9/kWh",
            "min": 3,
            "max": 15,
            "default_value": 8,
            "default_from": "city.electricity_tariff",
        },
        {
            "key": "annual_maintenance",
            "label": "Annual Maintenance / AMC",
            "type": "currency",
            "unit": "\u20b9/year",
            "min": 0,
            "max": 1000000,
            "default_value": 200000,
        },
        {
            "key": "filter_cost",
            "label": "Filter / Service Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 300000,
            "default_value": 50000,
        },
        {
            "key": "filter_frequency",
            "label": "Filter Services per Year",
            "type": "number",
            "unit": "/year",
            "min": 0,
            "max": 6,
            "default_value": 2,
        },
        {
            "key": "compressor_prob",
            "label": "Compressor Failure Probability",
            "type": "decimal",
            "unit": "0\u20131",
            "min": 0,
            "max": 1,
            "default_value": 0.15,
        },
        {
            "key": "compressor_cost",
            "label": "Compressor Replacement Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 300000,
            "max": 2000000,
            "default_value": 800000,
        },
    ],
    "ownership_years": OWNERSHIP_YEARS_DEFAULT,
    "presets": {
        "default": {},
        "conservative": {
            "electricity_price": 10,
            "annual_maintenance": 300000,
            "filter_cost": 70000,
            "compressor_prob": 0.25,
            "compressor_cost": 1000000,
        },
        "optimistic": {
            "electricity_price": 6,
            "annual_maintenance": 150000,
            "filter_cost": 35000,
            "compressor_prob": 0.05,
            "resale_value": 800000,
        },
    },
}

AC_COST_COMPONENTS = {
    "purchase": {
        "label": "Purchase Cost",
        "components": [
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "formula": "purchase_price",
            },
        ],
    },
    "ongoing_annual": {
        "label": "Annual Running Costs",
        "components": [
            {
                "name": "energy",
                "label": "Electricity",
                # electricity_price is in rupees → × 100 for paisa
                "formula": "annual_energy_kwh * electricity_price * 100",
            },
            {
                "name": "maintenance",
                "label": "Maintenance / AMC",
                "formula": "annual_maintenance",
            },
            {
                "name": "filters",
                "label": "Filter Services",
                "formula": "filter_cost * filter_frequency",
            },
        ],
    },
    "one_time_risk": {
        "label": "Potential Repairs",
        "components": [
            {
                "name": "compressor",
                "label": "Compressor Replacement (risk-weighted)",
                "formula": "compressor_prob * compressor_cost",
            },
        ],
    },
    "resale": {
        "label": "Resale Value",
        "components": [
            {
                "name": "resale",
                "label": "Estimated Resale",
                "formula": "0 - resale_value",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# 2. Air Purifier
#    HEPA-based room air purifier
# ---------------------------------------------------------------------------

AIR_PURIFIER_INPUT_SCHEMA = {
    "inputs": [
        {
            "key": "purchase_price",
            "label": "Purchase Price",
            "type": "currency",
            "unit": "\u20b9",
            "min": 500000,
            "max": 10000000,
            "default_value": 1500000,
            "default_from": "product.current_best_price",
        },
        {
            "key": "resale_value",
            "label": "Expected Resale Value",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 5000000,
            "default_value": 200000,
        },
        {
            "key": "filter_cost",
            "label": "HEPA Filter Replacement Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 50000,
            "max": 1500000,
            "default_value": 300000,
        },
        {
            "key": "filter_frequency",
            "label": "HEPA Filter Replacements per Year",
            "type": "decimal",
            "unit": "/year",
            "min": 0.5,
            "max": 4,
            "default_value": 2,
        },
        {
            "key": "annual_energy_kwh",
            "label": "Annual Energy Usage",
            "type": "number",
            "unit": "kWh/year",
            "min": 50,
            "max": 700,
            "default_value": 200,
        },
        {
            "key": "electricity_price",
            "label": "Electricity Price",
            "type": "decimal",
            "unit": "\u20b9/kWh",
            "min": 3,
            "max": 15,
            "default_value": 8,
            "default_from": "city.electricity_tariff",
        },
        {
            "key": "pre_filter_cost",
            "label": "Pre-filter / Carbon Filter Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 500000,
            "default_value": 80000,
        },
        {
            "key": "pre_filter_frequency",
            "label": "Pre-filter Replacements per Year",
            "type": "decimal",
            "unit": "/year",
            "min": 0,
            "max": 4,
            "default_value": 1,
        },
    ],
    "ownership_years": OWNERSHIP_YEARS_DEFAULT,
    "presets": {
        "default": {},
        "conservative": {
            "filter_cost": 400000,
            "filter_frequency": 3,
            "electricity_price": 10,
            "pre_filter_cost": 120000,
            "pre_filter_frequency": 2,
        },
        "optimistic": {
            "filter_cost": 250000,
            "filter_frequency": 1.5,
            "electricity_price": 6,
            "pre_filter_cost": 60000,
            "resale_value": 300000,
        },
    },
}

AIR_PURIFIER_COST_COMPONENTS = {
    "purchase": {
        "label": "Purchase Cost",
        "components": [
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "formula": "purchase_price",
            },
        ],
    },
    "ongoing_annual": {
        "label": "Annual Running Costs",
        "components": [
            {
                "name": "energy",
                "label": "Electricity",
                "formula": "annual_energy_kwh * electricity_price * 100",
            },
            {
                "name": "hepa_filters",
                "label": "HEPA Filter Replacement",
                "formula": "filter_cost * filter_frequency",
            },
            {
                "name": "pre_filters",
                "label": "Pre-filter / Carbon Filter",
                "formula": "pre_filter_cost * pre_filter_frequency",
            },
        ],
    },
    "one_time_risk": {
        "label": "Potential Repairs",
        "components": [],
    },
    "resale": {
        "label": "Resale Value",
        "components": [
            {
                "name": "resale",
                "label": "Estimated Resale",
                "formula": "0 - resale_value",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# 3. Water Purifier (RO)
#    RO + UV water purifier
# ---------------------------------------------------------------------------

WATER_PURIFIER_INPUT_SCHEMA = {
    "inputs": [
        {
            "key": "purchase_price",
            "label": "Purchase Price",
            "type": "currency",
            "unit": "\u20b9",
            "min": 500000,
            "max": 8000000,
            "default_value": 1800000,
            "default_from": "product.current_best_price",
        },
        {
            "key": "resale_value",
            "label": "Expected Resale Value",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 3000000,
            "default_value": 200000,
        },
        {
            "key": "cartridge_cost",
            "label": "Sediment + Carbon Cartridge Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 30000,
            "max": 500000,
            "default_value": 150000,
        },
        {
            "key": "cartridge_frequency",
            "label": "Cartridge Replacements per Year",
            "type": "number",
            "unit": "/year",
            "min": 1,
            "max": 4,
            "default_value": 2,
        },
        {
            "key": "membrane_cost",
            "label": "RO Membrane Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 100000,
            "max": 1000000,
            "default_value": 350000,
        },
        {
            "key": "membrane_frequency",
            "label": "Membrane Replacements per Year",
            "type": "decimal",
            "unit": "/year",
            "min": 0.2,
            "max": 1,
            "default_value": 0.5,
        },
        {
            "key": "water_consumption_lpd",
            "label": "Daily Purified Water Usage",
            "type": "number",
            "unit": "L/day",
            "min": 3,
            "max": 40,
            "default_value": 10,
        },
        {
            "key": "rejection_rate_pct",
            "label": "RO Water Rejection Rate",
            "type": "number",
            "unit": "%",
            "min": 0,
            "max": 80,
            "default_value": 60,
        },
        {
            "key": "water_price_per_kl",
            "label": "Water Tariff",
            "type": "decimal",
            "unit": "\u20b9/kL",
            "min": 10,
            "max": 200,
            "default_value": 50,
            "default_from": "city.water_tariff_per_kl",
        },
        {
            "key": "annual_energy_kwh",
            "label": "Annual Energy Usage",
            "type": "number",
            "unit": "kWh/year",
            "min": 20,
            "max": 400,
            "default_value": 100,
        },
        {
            "key": "electricity_price",
            "label": "Electricity Price",
            "type": "decimal",
            "unit": "\u20b9/kWh",
            "min": 3,
            "max": 15,
            "default_value": 8,
            "default_from": "city.electricity_tariff",
        },
        {
            "key": "annual_maintenance",
            "label": "Annual Maintenance / AMC",
            "type": "currency",
            "unit": "\u20b9/year",
            "min": 0,
            "max": 800000,
            "default_value": 150000,
        },
    ],
    "ownership_years": OWNERSHIP_YEARS_DEFAULT,
    "presets": {
        "default": {},
        "conservative": {
            "cartridge_cost": 200000,
            "membrane_cost": 450000,
            "electricity_price": 10,
            "annual_maintenance": 250000,
            "water_price_per_kl": 80,
            "rejection_rate_pct": 70,
        },
        "optimistic": {
            "cartridge_cost": 120000,
            "membrane_cost": 280000,
            "electricity_price": 6,
            "annual_maintenance": 100000,
            "water_price_per_kl": 30,
            "rejection_rate_pct": 50,
            "resale_value": 300000,
        },
    },
}

WATER_PURIFIER_COST_COMPONENTS = {
    "purchase": {
        "label": "Purchase Cost",
        "components": [
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "formula": "purchase_price",
            },
        ],
    },
    "ongoing_annual": {
        "label": "Annual Running Costs",
        "components": [
            {
                "name": "energy",
                "label": "Electricity",
                "formula": "annual_energy_kwh * electricity_price * 100",
            },
            {
                "name": "cartridges",
                "label": "Cartridge Replacement",
                "formula": "cartridge_cost * cartridge_frequency",
            },
            {
                "name": "membrane",
                "label": "RO Membrane Replacement",
                "formula": "membrane_cost * membrane_frequency",
            },
            {
                "name": "water_waste",
                "label": "Wasted Water (RO rejection)",
                # wasted L/day = consumed × rejection / (100 − rejection)
                # annual kL = wasted_lpd × 365 / 1000
                # cost in paisa = kL × tariff_rupees × 100
                "formula": "water_consumption_lpd * rejection_rate_pct / max(100 - rejection_rate_pct, 1) * 365 / 1000 * water_price_per_kl * 100",
            },
            {
                "name": "maintenance",
                "label": "Maintenance / AMC",
                "formula": "annual_maintenance",
            },
        ],
    },
    "one_time_risk": {
        "label": "Potential Repairs",
        "components": [],
    },
    "resale": {
        "label": "Resale Value",
        "components": [
            {
                "name": "resale",
                "label": "Estimated Resale",
                "formula": "0 - resale_value",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# 4. Refrigerator
#    Double-door frost-free refrigerator
# ---------------------------------------------------------------------------

REFRIGERATOR_INPUT_SCHEMA = {
    "inputs": [
        {
            "key": "purchase_price",
            "label": "Purchase Price",
            "type": "currency",
            "unit": "\u20b9",
            "min": 1000000,
            "max": 30000000,
            "default_value": 3000000,
            "default_from": "product.current_best_price",
        },
        {
            "key": "resale_value",
            "label": "Expected Resale Value",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 10000000,
            "default_value": 400000,
        },
        {
            "key": "annual_energy_kwh",
            "label": "Annual Energy Usage",
            "type": "number",
            "unit": "kWh/year",
            "min": 100,
            "max": 800,
            "default_value": 300,
        },
        {
            "key": "electricity_price",
            "label": "Electricity Price",
            "type": "decimal",
            "unit": "\u20b9/kWh",
            "min": 3,
            "max": 15,
            "default_value": 8,
            "default_from": "city.electricity_tariff",
        },
        {
            "key": "annual_maintenance",
            "label": "Annual Maintenance",
            "type": "currency",
            "unit": "\u20b9/year",
            "min": 0,
            "max": 800000,
            "default_value": 100000,
        },
        {
            "key": "compressor_prob",
            "label": "Compressor Failure Probability",
            "type": "decimal",
            "unit": "0\u20131",
            "min": 0,
            "max": 1,
            "default_value": 0.1,
        },
        {
            "key": "compressor_cost",
            "label": "Compressor Replacement Cost",
            "type": "currency",
            "unit": "\u20b9",
            "min": 200000,
            "max": 1500000,
            "default_value": 600000,
        },
    ],
    "ownership_years": OWNERSHIP_YEARS_LONG,
    "presets": {
        "default": {},
        "conservative": {
            "electricity_price": 10,
            "annual_maintenance": 200000,
            "compressor_prob": 0.2,
            "compressor_cost": 800000,
        },
        "optimistic": {
            "electricity_price": 6,
            "annual_maintenance": 50000,
            "compressor_prob": 0.03,
            "resale_value": 600000,
        },
    },
}

REFRIGERATOR_COST_COMPONENTS = {
    "purchase": {
        "label": "Purchase Cost",
        "components": [
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "formula": "purchase_price",
            },
        ],
    },
    "ongoing_annual": {
        "label": "Annual Running Costs",
        "components": [
            {
                "name": "energy",
                "label": "Electricity",
                "formula": "annual_energy_kwh * electricity_price * 100",
            },
            {
                "name": "maintenance",
                "label": "Maintenance",
                "formula": "annual_maintenance",
            },
        ],
    },
    "one_time_risk": {
        "label": "Potential Repairs",
        "components": [
            {
                "name": "compressor",
                "label": "Compressor Replacement (risk-weighted)",
                "formula": "compressor_prob * compressor_cost",
            },
        ],
    },
    "resale": {
        "label": "Resale Value",
        "components": [
            {
                "name": "resale",
                "label": "Estimated Resale",
                "formula": "0 - resale_value",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# 5. Washing Machine
#    Front-load / top-load washing machine
# ---------------------------------------------------------------------------

WASHING_MACHINE_INPUT_SCHEMA = {
    "inputs": [
        {
            "key": "purchase_price",
            "label": "Purchase Price",
            "type": "currency",
            "unit": "\u20b9",
            "min": 800000,
            "max": 15000000,
            "default_value": 2500000,
            "default_from": "product.current_best_price",
        },
        {
            "key": "resale_value",
            "label": "Expected Resale Value",
            "type": "currency",
            "unit": "\u20b9",
            "min": 0,
            "max": 6000000,
            "default_value": 300000,
        },
        {
            "key": "annual_energy_kwh",
            "label": "Annual Energy Usage",
            "type": "number",
            "unit": "kWh/year",
            "min": 50,
            "max": 500,
            "default_value": 150,
        },
        {
            "key": "electricity_price",
            "label": "Electricity Price",
            "type": "decimal",
            "unit": "\u20b9/kWh",
            "min": 3,
            "max": 15,
            "default_value": 8,
            "default_from": "city.electricity_tariff",
        },
        {
            "key": "water_per_cycle_liters",
            "label": "Water per Wash Cycle",
            "type": "number",
            "unit": "litres",
            "min": 20,
            "max": 150,
            "default_value": 60,
        },
        {
            "key": "cycles_per_week",
            "label": "Wash Cycles per Week",
            "type": "number",
            "unit": "/week",
            "min": 1,
            "max": 14,
            "default_value": 4,
        },
        {
            "key": "water_price_per_kl",
            "label": "Water Tariff",
            "type": "decimal",
            "unit": "\u20b9/kL",
            "min": 10,
            "max": 200,
            "default_value": 50,
            "default_from": "city.water_tariff_per_kl",
        },
        {
            "key": "detergent_cost_per_cycle",
            "label": "Detergent Cost per Cycle",
            "type": "currency",
            "unit": "\u20b9",
            "min": 300,
            "max": 3000,
            "default_value": 1000,
        },
        {
            "key": "annual_maintenance",
            "label": "Annual Maintenance",
            "type": "currency",
            "unit": "\u20b9/year",
            "min": 0,
            "max": 800000,
            "default_value": 150000,
        },
    ],
    "ownership_years": OWNERSHIP_YEARS_DEFAULT,
    "presets": {
        "default": {},
        "conservative": {
            "electricity_price": 10,
            "water_per_cycle_liters": 80,
            "cycles_per_week": 5,
            "water_price_per_kl": 80,
            "detergent_cost_per_cycle": 1500,
            "annual_maintenance": 250000,
        },
        "optimistic": {
            "electricity_price": 6,
            "water_per_cycle_liters": 45,
            "cycles_per_week": 3,
            "water_price_per_kl": 30,
            "detergent_cost_per_cycle": 700,
            "annual_maintenance": 100000,
            "resale_value": 500000,
        },
    },
}

WASHING_MACHINE_COST_COMPONENTS = {
    "purchase": {
        "label": "Purchase Cost",
        "components": [
            {
                "name": "purchase_price",
                "label": "Purchase Price",
                "formula": "purchase_price",
            },
        ],
    },
    "ongoing_annual": {
        "label": "Annual Running Costs",
        "components": [
            {
                "name": "energy",
                "label": "Electricity",
                "formula": "annual_energy_kwh * electricity_price * 100",
            },
            {
                "name": "water",
                "label": "Water Usage",
                # litres/cycle × cycles/week × 52 weeks / 1000 → kL/year
                # × tariff (₹/kL) × 100 → paisa
                "formula": "water_per_cycle_liters * cycles_per_week * 52 / 1000 * water_price_per_kl * 100",
            },
            {
                "name": "detergent",
                "label": "Detergent",
                "formula": "detergent_cost_per_cycle * cycles_per_week * 52",
            },
            {
                "name": "maintenance",
                "label": "Maintenance",
                "formula": "annual_maintenance",
            },
        ],
    },
    "one_time_risk": {
        "label": "Potential Repairs",
        "components": [],
    },
    "resale": {
        "label": "Resale Value",
        "components": [
            {
                "name": "resale",
                "label": "Estimated Resale",
                "formula": "0 - resale_value",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Master list: (category_slug, category_name, parent_slug, model_name,
#               input_schema, cost_components)
# ---------------------------------------------------------------------------

TCO_MODELS = [
    (
        "air-conditioners",
        "Air Conditioners",
        None,
        "Split AC \u2014 Total Cost of Ownership",
        AC_INPUT_SCHEMA,
        AC_COST_COMPONENTS,
    ),
    (
        "air-purifiers",
        "Air Purifiers",
        None,
        "Air Purifier \u2014 Total Cost of Ownership",
        AIR_PURIFIER_INPUT_SCHEMA,
        AIR_PURIFIER_COST_COMPONENTS,
    ),
    (
        "water-purifiers",
        "Water Purifiers",
        None,
        "Water Purifier (RO) \u2014 Total Cost of Ownership",
        WATER_PURIFIER_INPUT_SCHEMA,
        WATER_PURIFIER_COST_COMPONENTS,
    ),
    (
        "refrigerators",
        "Refrigerators",
        None,
        "Refrigerator \u2014 Total Cost of Ownership",
        REFRIGERATOR_INPUT_SCHEMA,
        REFRIGERATOR_COST_COMPONENTS,
    ),
    (
        "washing-machines",
        "Washing Machines",
        None,
        "Washing Machine \u2014 Total Cost of Ownership",
        WASHING_MACHINE_INPUT_SCHEMA,
        WASHING_MACHINE_COST_COMPONENTS,
    ),
]


# ---------------------------------------------------------------------------
# Management command
# ---------------------------------------------------------------------------


class Command(BaseCommand):
    help = "Seed TCOModel records for AC, Air Purifier, Water Purifier, Refrigerator, Washing Machine"

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing TCOModel records before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            count, _ = TCOModel.objects.all().delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} TCOModel record(s)."))

        created_count = 0
        updated_count = 0

        for slug, name, parent_slug, model_name, input_schema, cost_components in TCO_MODELS:
            # Ensure parent category exists (if any)
            parent = None
            if parent_slug:
                parent, _ = Category.objects.get_or_create(
                    slug=parent_slug,
                    defaults={"name": parent_slug.replace("-", " ").title(), "level": 0},
                )

            # Ensure category exists
            cat_defaults = {
                "name": name,
                "level": 1 if parent else 0,
                "has_tco_model": True,
            }
            if parent:
                cat_defaults["parent"] = parent

            category, cat_created = Category.objects.get_or_create(
                slug=slug,
                defaults=cat_defaults,
            )

            # Always ensure has_tco_model is True
            if not category.has_tco_model:
                category.has_tco_model = True
                category.save(update_fields=["has_tco_model"])

            if cat_created:
                self.stdout.write(f"  Created category: {name} ({slug})")

            # Upsert TCO model (unique on category + version)
            obj, created = TCOModel.objects.update_or_create(
                category=category,
                version=1,
                defaults={
                    "name": model_name,
                    "is_active": True,
                    "input_schema": input_schema,
                    "cost_components": cost_components,
                },
            )

            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f"  + Created: {model_name}"))
            else:
                updated_count += 1
                self.stdout.write(f"  ~ Updated: {model_name}")

        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {created_count} created, {updated_count} updated."
            )
        )
