"""Enrichment priority assigner + review target marker.

After lightweight records are created, this module assigns:
1. Enrichment priorities (P1=Playwright, P2=curl_cffi, P3=curl_cffi-low)
2. Review targets (top 100K products get review scraping after enrichment)

Before assignment, ``populate_derived_fields()`` fills ``current_price``
(from raw_price_data) and ``category_name`` (inferred from title regex)
for any records missing these values.

Both priority + review assignment run as UPDATE queries — ~2 seconds on 50K rows.
"""
from __future__ import annotations

import logging
import re
from decimal import Decimal, InvalidOperation

from django.db.models import Count, Q

from apps.pricing.models import BackfillProduct

logger = logging.getLogger(__name__)

# ── Scoring patterns ────────────────────────────────────────────────

TOP_BRANDS_PATTERN = (
    r'^(apple|samsung|oneplus|xiaomi|realme|vivo|oppo|'
    r'hp |dell |lenovo|asus|acer|sony|lg |boat |jbl |bose|'
    r'whirlpool|haier|google|nothing|motorola|nokia)'
)
TIER1_CATEGORIES_PATTERN = (
    r'(mobile|phone|smartphone|laptop|notebook|headphone|earphone|earbud|'
    r'television|tv|tablet|smartwatch|watch|iphone|galaxy|macbook|ipad|airpod)'
)
TIER2_CATEGORIES_PATTERN = (
    r'(refrigerator|washing.machine|air.conditioner|air.purifier|'
    r'camera|gaming|playstation|xbox|printer|monitor|speaker|soundbar|'
    r'router|hard.drive|ssd|power.bank|trimmer|iron)'
)

# ── Category inference ──────────────────────────────────────────────

# Ordered list: first match wins. More specific patterns first.
_CATEGORY_RULES: list[tuple[str, str]] = [
    (r'iphone', 'smartphone'),
    (r'galaxy\s*(s|z|a|m|f)\d', 'smartphone'),
    (r'(smartphone|mobile\s*phone)', 'smartphone'),
    (r'\bmobile\b', 'smartphone'),
    (r'\bphone\b', 'smartphone'),
    (r'macbook', 'laptop'),
    (r'(laptop|notebook|chromebook)', 'laptop'),
    (r'ipad', 'tablet'),
    (r'\btablet\b', 'tablet'),
    (r'airpod', 'earphone'),
    (r'(earbud|earphone|earbuds|in-ear|in.ear)', 'earphone'),
    (r'(headphone|headset|over-ear|over.ear)', 'headphone'),
    (r'(smartwatch|smart\s*watch|apple\s*watch|galaxy\s*watch)', 'smartwatch'),
    (r'\b(television|smart\s*tv|\btv\b|led\s*tv|oled|qled)\b', 'tv'),
    (r'(refrigerator|fridge|double\s*door|single\s*door)', 'refrigerator'),
    (r'(washing\s*machine|washer|front\s*load|top\s*load)', 'washing_machine'),
    (r'(air\s*conditioner|split\s*ac|window\s*ac|\bac\b.*ton)', 'air_conditioner'),
    (r'air\s*purifier', 'air_purifier'),
    (r'(dslr|mirrorless|camera\s*lens|\bcamera\b)', 'camera'),
    (r'(playstation|xbox|nintendo|gaming\s*console)', 'gaming_console'),
    (r'(gaming\s*laptop|gaming\s*mouse|gaming\s*keyboard|gaming)', 'gaming'),
    (r'\bprinter\b', 'printer'),
    (r'\bmonitor\b', 'monitor'),
    (r'(soundbar|sound\s*bar)', 'soundbar'),
    (r'(bluetooth\s*speaker|portable\s*speaker|\bspeaker\b)', 'speaker'),
    (r'\brouter\b', 'router'),
    (r'(hard\s*drive|hard\s*disk|\bhdd\b)', 'hard_drive'),
    (r'\bssd\b', 'ssd'),
    (r'(power\s*bank|portable\s*charger)', 'power_bank'),
    (r'\btrimmer\b', 'trimmer'),
    (r'\biron\b', 'iron'),
]
_CATEGORY_COMPILED = [(re.compile(pat, re.IGNORECASE), cat) for pat, cat in _CATEGORY_RULES]


def infer_category_from_title(title: str) -> str:
    """Infer product category from title using regex rules.

    Returns:
        Category slug (e.g. 'smartphone', 'laptop', 'tv') or '' if no match.
    """
    if not title:
        return ''
    for regex, category in _CATEGORY_COMPILED:
        if regex.search(title):
            return category
    return ''


# ── Derived field population ────────────────────────────────────────

def _extract_latest_price(raw_price_data: list[dict]) -> Decimal | None:
    """Extract the most recent price from raw_price_data JSONB."""
    if not raw_price_data:
        return None
    try:
        sorted_data = sorted(
            raw_price_data,
            key=lambda x: x.get('t', ''),
            reverse=True,
        )
        for entry in sorted_data:
            p = entry.get('p')
            if p:
                val = Decimal(str(p))
                if val > 0:
                    return val
    except (InvalidOperation, TypeError, ValueError):
        pass
    return None


def populate_derived_fields(batch_size: int = 5000) -> dict:
    """Fill current_price and category_name for records missing them.

    Processes in batches to avoid loading all records into memory.
    Should be called before assign_enrichment_priorities().

    Returns:
        Dict with counts of price_filled and category_filled.
    """
    price_filled = 0
    category_filled = 0

    # 1. Fill current_price from raw_price_data where missing
    qs_no_price = (
        BackfillProduct.objects
        .filter(current_price__isnull=True)
        .exclude(raw_price_data=[])
        .only('id', 'raw_price_data')
    )
    for bp in qs_no_price.iterator(chunk_size=batch_size):
        price = _extract_latest_price(bp.raw_price_data)
        if price:
            BackfillProduct.objects.filter(id=bp.id).update(current_price=price)
            price_filled += 1

    logger.info("Populated current_price for %d records", price_filled)

    # 2. Fill category_name from title where missing
    qs_no_cat = (
        BackfillProduct.objects
        .filter(category_name='')
        .exclude(title='')
        .only('id', 'title')
    )
    updates = []
    for bp in qs_no_cat.iterator(chunk_size=batch_size):
        cat = infer_category_from_title(bp.title)
        if cat:
            updates.append((bp.id, cat))
            if len(updates) >= batch_size:
                _bulk_update_category(updates)
                category_filled += len(updates)
                updates = []

    if updates:
        _bulk_update_category(updates)
        category_filled += len(updates)

    logger.info("Populated category_name for %d records", category_filled)
    return {'price_filled': price_filled, 'category_filled': category_filled}


def _bulk_update_category(updates: list[tuple]) -> None:
    """Bulk update category_name using CASE/WHEN for efficiency."""
    from django.db import connection

    if not updates:
        return
    # Build parameterized query to avoid SQL injection
    placeholders = []
    params = []
    for uid, cat in updates:
        placeholders.append("WHEN id = %s THEN %s")
        params.extend([str(uid), cat])

    case_expr = " ".join(placeholders)
    id_placeholders = ",".join(["%s"] * len(updates))
    id_params = [str(uid) for uid, _ in updates]
    params.extend(id_params)

    sql = (
        f"UPDATE backfill_products SET category_name = CASE {case_expr} END "
        f"WHERE id IN ({id_placeholders})"
    )
    with connection.cursor() as cur:
        cur.execute(sql, params)


# ── Priority assignment ─────────────────────────────────────────────

def assign_enrichment_priorities() -> dict:
    """Assign P1/P2/P3 based on tracker signals.

    Returns:
        Dict with p1 and p2 counts updated.
    """
    base_qs = BackfillProduct.objects.filter(
        scrape_status='pending',
        enrichment_priority=3,
    )

    # P1: Playwright targets — high-value, popular, or tier-1 category
    p1_count = base_qs.filter(
        Q(price_data_points__gte=200)
        | Q(category_name__iregex=TIER1_CATEGORIES_PATTERN)
        | Q(title__iregex=TOP_BRANDS_PATTERN, current_price__gte=1000000)
    ).filter(current_price__gt=0).update(enrichment_priority=1)

    logger.info("Assigned %d products to P1 (Playwright)", p1_count)

    # P2: curl_cffi targets — moderate signals
    # Re-filter base_qs since P1 already updated some rows
    p2_count = base_qs.filter(enrichment_priority=3).filter(
        Q(price_data_points__gte=50)
        | Q(current_price__gte=500000, current_price__lte=20000000)
        | Q(marketplace_slug='amazon-in', price_data_points__gte=30)
        | Q(category_name__iregex=TIER2_CATEGORIES_PATTERN)
    ).filter(current_price__gt=0).update(enrichment_priority=2)

    logger.info("Assigned %d products to P2 (curl_cffi)", p2_count)

    # P3: everything else stays at default 3 (curl_cffi-low)

    # Log distribution
    dist = (
        BackfillProduct.objects.filter(scrape_status='pending')
        .values('enrichment_priority')
        .annotate(count=Count('id'))
        .order_by('enrichment_priority')
    )
    for row in dist:
        logger.info("  P%d: %s", row['enrichment_priority'], f"{row['count']:,}")

    return {'p1': p1_count, 'p2': p2_count}


# ── Custom priority rules (admin-configurable) ────────────────────

def apply_custom_priority_rules() -> dict:
    """Apply admin-defined EnrichmentPriorityRule records.

    Rules are evaluated in ``order`` (ascending). Each rule builds a queryset
    from its filters and bulk-updates matching products to the target priority.
    Later rules can override earlier ones (higher ``order`` wins).

    Returns:
        Dict with per-rule counts and total updated.
    """
    from apps.pricing.models import EnrichmentPriorityRule

    rules = EnrichmentPriorityRule.objects.filter(is_active=True).order_by("order")
    results = []
    total = 0

    for rule in rules:
        qs = rule.build_queryset()
        count = qs.update(enrichment_priority=rule.target_priority)

        if rule.also_mark_reviews and count > 0:
            # Mark matched products for review scraping
            review_updated = qs.filter(review_status="skip").update(
                review_status="pending",
            )
            logger.info(
                "  Rule '%s': %d → P%d (%d marked for reviews)",
                rule.name, count, rule.target_priority, review_updated,
            )
        else:
            logger.info(
                "  Rule '%s': %d → P%d", rule.name, count, rule.target_priority,
            )

        results.append({
            "rule": rule.name,
            "target_priority": rule.target_priority,
            "updated": count,
        })
        total += count

    logger.info("Custom rules applied: %d total updates from %d rules", total, len(results))
    return {"rules": results, "total": total}


# ── Review target assignment ────────────────────────────────────────

def assign_review_targets(max_review_products: int = 100_000) -> int:
    """Mark top products for review scraping.

    Run AFTER assign_enrichment_priorities. All P1 products get reviews,
    then fill remaining quota from P2 ordered by popularity
    (price_data_points desc).

    Args:
        max_review_products: Maximum number of products to mark for reviews.

    Returns:
        Total number of products marked for review scraping.
    """
    # All P1 products get reviews
    p1_count = BackfillProduct.objects.filter(
        enrichment_priority=1,
        review_status='skip',
    ).update(review_status='pending')

    logger.info("Marked %d P1 products for review scraping", p1_count)

    remaining = max_review_products - p1_count
    if remaining > 0:
        # Fill from P2, ordered by popularity (price_data_points desc)
        p2_ids = list(
            BackfillProduct.objects.filter(
                enrichment_priority=2,
                review_status='skip',
            )
            .order_by('-price_data_points')
            .values_list('id', flat=True)[:remaining]
        )
        if p2_ids:
            BackfillProduct.objects.filter(id__in=p2_ids).update(
                review_status='pending',
            )
            logger.info("Marked %d P2 products for review scraping", len(p2_ids))
            p1_count += len(p2_ids)

    total = BackfillProduct.objects.filter(review_status='pending').count()
    logger.info("Review targets: %s products marked for review scraping", f"{total:,}")
    return total
