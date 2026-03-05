"""Celery tasks for DudScore and Brand Trust Score computation."""
import json
import logging
from decimal import Decimal

from celery import shared_task
from django.db import connection
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(queue="scoring", bind=True, max_retries=2, default_retry_delay=60)
def compute_dudscore(self, product_id: str) -> dict | None:
    """Compute DudScore v1 for a single product using the current active config.

    Workflow:
      1. Load the active DudScoreConfig (weights).
      2. Run all 6 component calculators + fraud/confidence multipliers.
      3. Compute weighted sum x fraud x confidence -> normalize to 0-100.
      4. Spike detection: log warning if delta > threshold (save anyway for v1).
      5. Write DudScoreHistory row via raw SQL (hypertable, no auto PK).
      6. Update Product.dud_score, dud_score_confidence, dud_score_updated_at.
      7. Return summary dict.
    """
    from apps.products.models import Product
    from apps.scoring.components import compute_all_components
    from apps.scoring.models import DudScoreConfig

    # 1. Load active config
    config = DudScoreConfig.objects.filter(is_active=True).order_by("-version").first()
    if not config:
        logger.error("compute_dudscore: no active DudScoreConfig found")
        return None

    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        logger.error("compute_dudscore: product %s not found", product_id)
        return None

    # 2. Compute all components
    components = compute_all_components(str(product_id))

    # 3. Weighted sum (each component is 0-1, weights sum to 1.0)
    raw_score = (
        float(config.w_sentiment) * components.sentiment
        + float(config.w_rating_quality) * components.rating_quality
        + float(config.w_price_value) * components.price_value
        + float(config.w_review_credibility) * components.review_credibility
        + float(config.w_price_stability) * components.price_stability
        + float(config.w_return_signal) * components.return_signal
    )

    # Scale to 0-100 then apply multipliers
    final_score = raw_score * 100.0 * components.fraud_multiplier * components.confidence_multiplier
    final_score = max(0.0, min(100.0, round(final_score, 2)))

    # 4. Spike detection
    old_score = float(product.dud_score) if product.dud_score is not None else None
    if old_score is not None:
        delta = abs(final_score - old_score)
        spike_threshold = (
            float(config.anomaly_spike_threshold)
            if config.anomaly_spike_threshold
            else 15.0
        )
        if delta > spike_threshold:
            logger.warning(
                "DudScore SPIKE: product=%s old=%.2f new=%.2f delta=%.2f threshold=%.2f",
                product_id, old_score, final_score, delta, spike_threshold,
            )

    # 5. Write DudScoreHistory (raw SQL — hypertable has no auto PK)
    now = timezone.now()
    component_scores_json = json.dumps({
        "sentiment": round(components.sentiment * 100, 2),
        "rating_quality": round(components.rating_quality * 100, 2),
        "price_value": round(components.price_value * 100, 2),
        "review_credibility": round(components.review_credibility * 100, 2),
        "price_stability": round(components.price_stability * 100, 2),
        "return_signal": round(components.return_signal * 100, 2),
        "fraud_multiplier": round(components.fraud_multiplier, 4),
        "confidence_multiplier": round(components.confidence_multiplier, 4),
    })

    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO "scoring"."dudscore_history"
                (time, product_id, score, config_version, component_scores)
            VALUES (%s, %s, %s, %s, %s)
            """,
            [now, str(product_id), final_score, config.version, component_scores_json],
        )

    # 6. Update product
    product.dud_score = Decimal(str(final_score))
    product.dud_score_confidence = components.confidence_label
    product.dud_score_updated_at = now
    product.save(update_fields=["dud_score", "dud_score_confidence", "dud_score_updated_at"])

    logger.info(
        "compute_dudscore: product=%s score=%.2f confidence=%s config_v%d",
        product_id, final_score, components.confidence_label, config.version,
    )

    # 7. Return summary
    return {
        "product_id": str(product_id),
        "score": final_score,
        "confidence": components.confidence_label,
        "config_version": config.version,
        "components": {
            "sentiment": round(components.sentiment, 4),
            "rating_quality": round(components.rating_quality, 4),
            "price_value": round(components.price_value, 4),
            "review_credibility": round(components.review_credibility, 4),
            "price_stability": round(components.price_stability, 4),
            "return_signal": round(components.return_signal, 4),
        },
        "fraud_multiplier": round(components.fraud_multiplier, 4),
        "confidence_multiplier": round(components.confidence_multiplier, 4),
    }


@shared_task(queue="scoring")
def full_dudscore_recalculation() -> dict:
    """Monthly: recalculate DudScore for ALL active products.

    Fans out individual ``compute_dudscore`` tasks for Celery concurrency
    and fault isolation — a failure on one product does not block others.
    """
    from apps.products.models import Product

    product_ids = list(
        Product.objects.filter(status=Product.Status.ACTIVE)
        .values_list("id", flat=True)
    )

    dispatched = 0
    for pid in product_ids:
        compute_dudscore.delay(str(pid))
        dispatched += 1

    logger.info("full_dudscore_recalculation: dispatched %d tasks", dispatched)
    return {"dispatched": dispatched, "total_products": len(product_ids)}


def _derive_trust_tier(avg_score: float) -> str:
    """Map an average DudScore to a trust tier label."""
    if avg_score >= 80:
        return "excellent"
    if avg_score >= 65:
        return "good"
    if avg_score >= 50:
        return "average"
    if avg_score >= 35:
        return "poor"
    return "avoid"


@shared_task(queue="scoring")
def recompute_brand_trust_scores() -> dict:
    """Weekly: recompute BrandTrustScore for all qualifying brands.

    A brand qualifies when it has >= ``BrandTrustConfig.min_products`` products
    with a non-NULL dud_score.

    Metrics computed per brand:
      - avg_dud_score: AVG(dud_score) of scored products
      - product_count: COUNT of scored products
      - avg_fake_review_pct: AVG fake-review % across products
      - avg_price_stability: AVG price_stability component from latest DudScoreHistory
      - quality_consistency: STDDEV(dud_score) — lower = more consistent
      - trust_tier: derived from avg_dud_score
    """
    from django.db.models import Avg, Count, Q, StdDev

    from apps.products.models import Brand, Product
    from apps.scoring.models import BrandTrustScore

    from common.app_settings import BrandTrustConfig

    min_products = BrandTrustConfig.min_products()
    now = timezone.now()

    # Find brands with enough scored products
    qualifying_brands = (
        Brand.objects.annotate(
            scored_count=Count(
                "products",
                filter=Q(products__dud_score__isnull=False, products__status=Product.Status.ACTIVE),
            ),
        )
        .filter(scored_count__gte=min_products)
    )

    updated = 0
    created = 0

    for brand in qualifying_brands:
        scored_products = Product.objects.filter(
            brand=brand,
            dud_score__isnull=False,
            status=Product.Status.ACTIVE,
        )

        agg = scored_products.aggregate(
            avg_score=Avg("dud_score"),
            stddev_score=StdDev("dud_score"),
            count=Count("id"),
        )

        avg_dud_score = float(agg["avg_score"] or 0)
        product_count = agg["count"] or 0
        quality_consistency = float(agg["stddev_score"]) if agg["stddev_score"] is not None else None

        # Avg fake review percentage: ratio of flagged reviews per product
        avg_fake_review_pct = _compute_avg_fake_review_pct(scored_products)

        # Avg price stability from most recent DudScoreHistory per product
        avg_price_stability = _compute_avg_price_stability(scored_products)

        trust_tier = _derive_trust_tier(avg_dud_score)

        _, was_created = BrandTrustScore.objects.update_or_create(
            brand=brand,
            defaults={
                "avg_dud_score": Decimal(str(round(avg_dud_score, 2))),
                "product_count": product_count,
                "avg_fake_review_pct": (
                    Decimal(str(round(avg_fake_review_pct, 2)))
                    if avg_fake_review_pct is not None
                    else None
                ),
                "avg_price_stability": (
                    Decimal(str(round(avg_price_stability, 2)))
                    if avg_price_stability is not None
                    else None
                ),
                "quality_consistency": (
                    Decimal(str(round(quality_consistency, 2)))
                    if quality_consistency is not None
                    else None
                ),
                "trust_tier": trust_tier,
                "computed_at": now,
            },
        )

        if was_created:
            created += 1
        else:
            updated += 1

    # Clean up brand trust scores for brands that no longer qualify
    stale = BrandTrustScore.objects.exclude(
        brand__in=qualifying_brands,
    )
    stale_count = stale.count()
    if stale_count:
        logger.info("recompute_brand_trust_scores: removing %d stale scores", stale_count)
        stale.delete()

    logger.info(
        "recompute_brand_trust_scores: created=%d updated=%d removed=%d",
        created, updated, stale_count,
    )
    return {"created": created, "updated": updated, "removed": stale_count}


def _compute_avg_fake_review_pct(scored_products) -> float | None:
    """Compute average fake review percentage across a queryset of products."""
    from apps.reviews.models import Review

    product_ids = list(scored_products.values_list("id", flat=True))
    if not product_ids:
        return None

    # For each product: flagged_count / total_count * 100
    totals = []
    for pid in product_ids:
        reviews = Review.objects.filter(product_id=pid, status="published")
        total = reviews.count()
        if total == 0:
            continue
        flagged = reviews.filter(is_flagged=True).count()
        totals.append((flagged / total) * 100)

    return sum(totals) / len(totals) if totals else None


def _compute_avg_price_stability(scored_products) -> float | None:
    """Compute average price stability component from latest DudScoreHistory entries."""
    product_ids = list(scored_products.values_list("id", flat=True))
    if not product_ids:
        return None

    # Use raw SQL to get the most recent component_scores per product
    # and extract the price_stability value from JSONB
    placeholders = ", ".join(["%s"] * len(product_ids))
    query = f"""
        SELECT AVG((component_scores->>'price_stability')::numeric)
        FROM (
            SELECT DISTINCT ON (product_id) product_id, component_scores
            FROM "scoring"."dudscore_history"
            WHERE product_id = ANY(%s)
            ORDER BY product_id, time DESC
        ) latest
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [list(str(pid) for pid in product_ids)])
        row = cursor.fetchone()

    if row and row[0] is not None:
        return float(row[0])
    return None
