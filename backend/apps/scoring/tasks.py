"""Celery tasks for DudScore computation."""
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
