"""Product matching engine — cross-marketplace deduplication.

Implements the 4-step matching process from ARCHITECTURE.md Section 6, Stage 3:
  1. Extract canonical identifiers (brand, model, variant, EAN)
  2. Score candidates against existing products
  3. Create or merge based on confidence thresholds
  4. Update canonical product aggregates

Used by ProductPipeline in scraping/pipelines.py.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from decimal import Decimal
from difflib import SequenceMatcher
from typing import NamedTuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class MatchResult:
    """Outcome of the product matching pipeline."""

    product: object  # apps.products.models.Product
    confidence: float
    method: str  # ean | brand_model_variant | brand_model | fuzzy_title | new
    is_new: bool


class ModelInfo(NamedTuple):
    """Extracted model and variant components from a product title."""

    model: str       # e.g. "Galaxy S24 FE 5G"
    storage: str     # e.g. "256GB" or ""
    ram: str         # e.g. "8GB" or ""
    color: str       # e.g. "Mint" or ""


# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Storage: 128GB, 256 GB, 1TB
_STORAGE_RE = re.compile(r'(\d+)\s*(GB|TB)', re.IGNORECASE)

# RAM: 8GB RAM, 8 GB RAM (must appear before generic storage extraction)
_RAM_RE = re.compile(r'(\d+)\s*GB\s*RAM', re.IGNORECASE)

# Color: first parenthesised word group — e.g. "(Mint, 8GB, 256GB)" → "Mint"
_PAREN_COLOR_RE = re.compile(r'\(([A-Za-z][A-Za-z ]+?)(?:,|\))')

# Common barcode spec key names (lowercased for comparison)
_EAN_KEYS = frozenset({
    "ean", "ean13", "gtin", "gtin13", "gtin14",
    "upc", "barcode", "item model number",
})


# ===================================================================
# Public API
# ===================================================================

def match_product(item, brand=None, category=None) -> MatchResult:
    """Match a scraped item to a canonical product.

    Args:
        item: A scrapy ProductItem dict-like with title, brand, specs, etc.
        brand: Pre-resolved Brand instance (optional). If *None* and
               ``item["brand"]`` is set, brand resolution runs internally.
        category: Pre-resolved Category instance (optional).

    Returns:
        MatchResult with the matched (or newly created) Product,
        confidence score, match method, and whether it's a new product.
    """
    # Step 1 — Extract canonical identifiers
    if brand is None and item.get("brand"):
        brand = _resolve_brand(item["brand"])

    ean = _extract_ean(item.get("specs") or {})
    model_info = _extract_model_info(
        item["title"], brand.name if brand else "",
    )

    # Step 2 — Match scoring
    result = _find_best_match(item, brand, model_info, ean)

    if result is not None:
        product, confidence, method = result
        # Backfill category on existing product if missing
        if category and not product.category:
            product.category = category
            product.save(update_fields=["category", "updated_at"])
        logger.info(
            "Matched '%s' → product %s (confidence=%.2f, method=%s)",
            item["title"][:60],
            getattr(product, "slug", "?")[:40],
            confidence,
            method,
        )
        return MatchResult(
            product=product,
            confidence=confidence,
            method=method,
            is_new=False,
        )

    # Step 3 — Low confidence: create new canonical product
    product = _create_canonical_product(item, brand, category)
    return MatchResult(
        product=product,
        confidence=1.0,
        method="new",
        is_new=True,
    )


def resolve_category(slug: str | None):
    """Resolve a category slug to a Category instance, creating it if missing."""
    if not slug:
        return None

    from apps.products.models import Category

    category = Category.objects.filter(slug=slug).first()
    if category:
        return category

    # Auto-create with a human-readable name derived from slug
    name = slug.replace("-", " ").replace("_", " ").title()
    category, _ = Category.objects.get_or_create(
        slug=slug,
        defaults={"name": name, "level": 0},
    )
    logger.info("Auto-created category: %s (%s)", name, slug)
    return category


def resolve_or_create_brand(raw_brand: str):
    """Resolve a brand string via aliases, or create a new Brand record.

    This replaces the pipeline's bare ``Brand.objects.get_or_create`` by
    first checking Brand.aliases for known synonyms (e.g. "MI" → Xiaomi).
    """
    from django.utils.text import slugify

    from apps.products.models import Brand

    if not raw_brand:
        return None

    # Check aliases first
    brand = _resolve_brand(raw_brand)
    if brand:
        return brand

    # Fallback: get-or-create by slug
    brand, _ = Brand.objects.get_or_create(
        slug=slugify(raw_brand),
        defaults={"name": raw_brand},
    )
    return brand


def update_canonical_product(product) -> None:
    """Step 4 — Recalculate canonical product aggregates from ALL listings.

    Updates: avg_rating (weighted), total_reviews, current_best_price,
    current_best_marketplace, lowest_price_ever, lowest_price_date.
    """
    from datetime import date

    from django.db.models import F, Sum

    from apps.products.models import ProductListing

    listings = ProductListing.objects.filter(product=product)

    update_fields = [
        "avg_rating", "total_reviews",
        "current_best_price", "current_best_marketplace",
        "updated_at",
    ]

    # ---- Rating & reviews (weighted average) ----
    agg = listings.filter(
        rating__isnull=False, review_count__gt=0,
    ).aggregate(
        total_reviews=Sum("review_count"),
        weighted_sum=Sum(F("rating") * F("review_count")),
    )

    total = agg["total_reviews"] or 0
    product.total_reviews = total
    if total > 0 and agg["weighted_sum"]:
        product.avg_rating = Decimal(str(
            round(float(agg["weighted_sum"]) / total, 2)
        ))
    else:
        product.avg_rating = None

    # ---- Best price across in-stock listings ----
    cheapest = (
        listings.filter(in_stock=True, current_price__isnull=False)
        .order_by("current_price")
        .values_list("current_price", "marketplace__slug")
        .first()
    )

    # Fall back to any listing with a price (even OOS) so cards always show a price
    if not cheapest:
        cheapest = (
            listings.filter(current_price__isnull=False)
            .order_by("current_price")
            .values_list("current_price", "marketplace__slug")
            .first()
        )

    if cheapest:
        product.current_best_price = cheapest[0]
        product.current_best_marketplace = cheapest[1]

        if (
            product.lowest_price_ever is None
            or cheapest[0] < product.lowest_price_ever
        ):
            product.lowest_price_ever = cheapest[0]
            product.lowest_price_date = date.today()
            update_fields.extend(["lowest_price_ever", "lowest_price_date"])
    else:
        product.current_best_price = None
        product.current_best_marketplace = ""

    product.save(update_fields=update_fields)


# ===================================================================
# Step 1 helpers — identifier extraction
# ===================================================================

def _resolve_brand(raw_brand: str):
    """Look up a Brand by slug or aliases."""
    from django.utils.text import slugify

    from apps.products.models import Brand

    if not raw_brand:
        return None

    slug = slugify(raw_brand)

    # Direct slug match (fast path)
    brand = Brand.objects.filter(slug=slug).first()
    if brand:
        return brand

    # Check Brand.aliases JSONField — list of alternative names
    raw_lower = raw_brand.lower().strip()
    for brand in Brand.objects.exclude(aliases=[]).iterator():
        if any(alias.lower() == raw_lower for alias in brand.aliases):
            return brand

    return None


def _extract_ean(specs: dict) -> str | None:
    """Extract EAN/GTIN/UPC barcode from product specs if present."""
    if not specs:
        return None

    for spec_key, spec_val in specs.items():
        if spec_key.lower().strip() in _EAN_KEYS:
            cleaned = re.sub(r"\D", "", str(spec_val))
            if 8 <= len(cleaned) <= 14:
                return cleaned

    return None


def _extract_model_info(title: str, brand_name: str) -> ModelInfo:
    """Parse model name and variant components from a product title.

    Examples:
        "Samsung Galaxy S24 FE 5G (Mint, 8GB, 256GB)"
        → ModelInfo(model="Galaxy S24 FE 5G", storage="256GB", ram="8GB", color="Mint")

        "APPLE iPhone 15 Pro Max (Natural Titanium, 256 GB)"
        → ModelInfo(model="iPhone 15 Pro Max", storage="256GB", ram="", color="Natural Titanium")
    """
    # Remove brand name from title
    if brand_name:
        clean = re.sub(
            re.escape(brand_name), "", title, count=1, flags=re.IGNORECASE,
        ).strip()
    else:
        clean = title.strip()

    # Extract RAM first (so "8GB RAM" isn't mistaken for storage)
    ram = ""
    m = _RAM_RE.search(clean)
    if m:
        ram = f"{m.group(1)}GB"

    # Extract storage (skip if part of a "...GB RAM" match)
    storage = ""
    for m in _STORAGE_RE.finditer(clean):
        # Check that this isn't the RAM we already captured
        after = clean[m.end():m.end() + 10]
        if re.match(r"\s*RAM", after, re.IGNORECASE):
            continue
        storage = f"{m.group(1)}{m.group(2).upper()}"
        break  # take the first non-RAM storage mention

    # Extract color from parenthetical
    color = ""
    m = _PAREN_COLOR_RE.search(clean)
    if m:
        candidate = m.group(1).strip()
        if not re.match(r"^\d", candidate):
            color = candidate

    # Model = title minus brand, variant info, and parenthetical content
    model = re.sub(r"\([^)]*\)", " ", clean)       # Remove (...)
    model = _RAM_RE.sub(" ", model)                 # Remove RAM
    model = _STORAGE_RE.sub(" ", model)             # Remove storage
    model = re.sub(
        r"\b\d+\s*(MP|W|mAh|Wh|mm)\b", " ", model, flags=re.IGNORECASE,
    )
    model = re.sub(r"[-–—,]+\s*$", "", model)      # Trailing punctuation
    model = re.sub(r"\s+", " ", model).strip()

    return ModelInfo(model=model, storage=storage, ram=ram, color=color)


# ===================================================================
# Step 2 helpers — match scoring
# ===================================================================

def _match_by_ean(ean: str):
    """Find an active product whose specs contain this barcode value."""
    from apps.products.models import Product

    key_variants = [
        "EAN", "ean", "GTIN", "gtin", "UPC", "upc",
        "Barcode", "barcode", "EAN13", "ean13",
    ]

    # Fast path: exact JSONB key→value lookup
    for key in key_variants:
        try:
            product = Product.objects.filter(
                status=Product.Status.ACTIVE,
                **{f"specs__{key}": ean},
            ).first()
            if product:
                return product
        except Exception:
            continue

    # Fallback: strip non-digits and compare (handles "8 901234 567890")
    for key in key_variants[:6]:
        try:
            for product in (
                Product.objects.filter(
                    status=Product.Status.ACTIVE,
                    specs__has_key=key,
                )[:100]
            ):
                val = re.sub(r"\D", "", str(product.specs.get(key, "")))
                if val == ean:
                    return product
        except Exception:
            continue

    return None


def _normalize_model_str(s: str) -> str:
    """Lowercase, collapse whitespace, strip non-alphanumeric edges."""
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _models_match(
    a: ModelInfo,
    b: ModelInfo,
    *,
    exact_variant: bool,
) -> bool:
    """Compare two ModelInfo objects.

    Args:
        exact_variant: If True, storage and RAM must also match.
    """
    if not a.model or not b.model:
        return False

    a_norm = _normalize_model_str(a.model)
    b_norm = _normalize_model_str(b.model)

    # Model names must be very similar (≥ 0.90 ratio)
    if SequenceMatcher(None, a_norm, b_norm).ratio() < 0.90:
        return False

    if exact_variant:
        # Storage must match when both have it
        if a.storage and b.storage and a.storage != b.storage:
            return False
        # RAM must match when both have it
        if a.ram and b.ram and a.ram != b.ram:
            return False
        # If one has storage and the other doesn't, can't confirm exact match
        if bool(a.storage) != bool(b.storage):
            return False

    return True


def _find_best_match(item, brand, model_info: ModelInfo, ean: str | None):
    """Run matching strategies in priority order.

    Returns ``(product, confidence, method)`` or ``None``.
    """
    from common.app_settings import MatchingConfig

    from apps.products.models import Product

    # ---- Strategy 1: EAN exact match → confidence 1.0 ----
    if ean:
        product = _match_by_ean(ean)
        if product:
            return (product, 1.0, "ean")

    if not brand:
        return None

    # Fetch candidates — same brand, active
    max_candidates = MatchingConfig.max_candidates()
    candidates = list(
        Product.objects.filter(brand=brand, status=Product.Status.ACTIVE)
        .values_list("id", "title")[:max_candidates]
    )

    if not candidates:
        return None

    # Precompute model info for all candidates (once)
    candidate_data = [
        (pid, ctitle, _extract_model_info(ctitle, brand.name))
        for pid, ctitle in candidates
    ]

    # ---- Strategy 2: Brand + model + variant exact → confidence 0.95 ----
    if model_info.model:
        for pid, ctitle, c_model in candidate_data:
            if _models_match(model_info, c_model, exact_variant=True):
                product = Product.objects.get(id=pid)
                return (product, 0.95, "brand_model_variant")

    # ---- Strategy 3: Brand + model (variant differs) → confidence 0.85 ----
    if model_info.model:
        for pid, ctitle, c_model in candidate_data:
            if _models_match(model_info, c_model, exact_variant=False):
                product = Product.objects.get(id=pid)
                return (product, 0.85, "brand_model")

    # ---- Strategy 4: Fuzzy title match → confidence 0.70 ----
    title_lower = item["title"].lower()
    best_pid = None
    best_ratio = 0.0

    for pid, ctitle, _ in candidate_data:
        ratio = SequenceMatcher(None, title_lower, ctitle.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_pid = pid

    fuzzy_threshold = MatchingConfig.fuzzy_title_threshold()
    if best_ratio >= fuzzy_threshold and best_pid:
        product = Product.objects.get(id=best_pid)
        return (product, 0.70, "fuzzy_title")

    # No match found — caller will create a new product
    return None


# ===================================================================
# Step 3 helper — create new canonical product
# ===================================================================

def _create_canonical_product(item, brand, category=None):
    """Create a new canonical Product when no match is found."""
    from django.utils import timezone
    from django.utils.text import slugify

    from apps.products.models import Product

    now = timezone.now()

    base_slug = slugify(item["title"][:200])
    slug = base_slug
    counter = 1
    while Product.objects.filter(slug=slug).exists():
        slug = f"{base_slug}-{counter}"
        counter += 1

    product = Product.objects.create(
        slug=slug,
        title=item["title"],
        brand=brand,
        category=category,
        description="",
        specs=item.get("specs") or {},
        images=item.get("images") or [],
        avg_rating=item.get("rating"),
        total_reviews=item.get("review_count") or 0,
        current_best_price=item.get("price"),
        current_best_marketplace=item.get("marketplace_slug", ""),
        status=Product.Status.ACTIVE,
        last_scraped_at=now,
    )
    logger.info("Created new canonical product: %s (category=%s)", product.slug, category)
    return product
