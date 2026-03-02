"""DudScore v1 component calculators.

Each ``calculate_*`` function returns a float in [0.0, 1.0].
Multiplier helpers return floats in their documented ranges.

All heavy queries are time-bounded and use pre-computed fields on
Review where available (falling back to TextBlob for sentiment).

Dependencies: textblob, numpy (both in requirements/base.txt).
"""
import logging
import math
from datetime import date, timedelta
from decimal import Decimal
from typing import NamedTuple

import numpy as np
from django.db.models import Q
from django.utils import timezone
from textblob import TextBlob

from common.app_settings import ScoringConfig

logger = logging.getLogger(__name__)


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Component 1: Sentiment Score
# ---------------------------------------------------------------------------

def calculate_sentiment_score(product_id: str) -> float:
    """Weighted-average sentiment polarity across published reviews.

    * Uses pre-computed ``Review.sentiment_score`` when available.
    * Falls back to TextBlob for reviews without a score, and backfills.
    * Recent reviews weighted via exponential decay (half-life 90 days).
    * Verified purchases weighted 2x.

    Returns 0.5 (neutral) when no data is available.
    """
    from apps.reviews.models import Review

    reviews = list(
        Review.objects.filter(product_id=product_id, is_published=True)
        .values_list("id", "sentiment_score", "is_verified_purchase",
                      "review_date", "created_at", "body")
    )

    if not reviews:
        return 0.5

    half_life = ScoringConfig.sentiment_half_life_days()
    vp_weight = ScoringConfig.verified_purchase_weight()
    now = timezone.now().date()

    weighted_sum = 0.0
    weight_total = 0.0
    backfill: list[tuple] = []  # (review_id, sentiment_float)

    for rid, sent_score, is_vp, review_date, created_at, body in reviews:
        # Determine sentiment value
        if sent_score is not None:
            sentiment = float(sent_score)
        elif body and len(body.strip()) > 0:
            polarity = TextBlob(body).sentiment.polarity  # -1 to +1
            sentiment = _clamp((polarity + 1.0) / 2.0)
            backfill.append((rid, sentiment))
        else:
            continue  # skip reviews with no sentiment data at all

        # Time weight: 2^(-age_days / half_life)
        ref_date = review_date or (created_at.date() if created_at else now)
        age_days = max((now - ref_date).days, 0)
        w_time = math.pow(2.0, -age_days / half_life) if half_life > 0 else 1.0

        # Verified purchase multiplier
        w = w_time * (vp_weight if is_vp else 1.0)

        weighted_sum += sentiment * w
        weight_total += w

    # Backfill sentiment_score on reviews that were missing it
    if backfill:
        from apps.reviews.models import Review as ReviewModel
        objs = ReviewModel.objects.filter(id__in=[b[0] for b in backfill])
        obj_map = {str(o.id): o for o in objs}
        to_update = []
        for rid, sval in backfill:
            obj = obj_map.get(str(rid))
            if obj:
                obj.sentiment_score = Decimal(str(round(sval, 2)))
                obj.sentiment_label = (
                    "positive" if sval >= 0.6 else
                    "negative" if sval <= 0.4 else
                    "neutral"
                )
                to_update.append(obj)
        if to_update:
            ReviewModel.objects.bulk_update(
                to_update, ["sentiment_score", "sentiment_label"], batch_size=500
            )

    if weight_total == 0.0:
        return 0.5

    return _clamp(weighted_sum / weight_total)


# ---------------------------------------------------------------------------
# Component 2: Rating Quality Score
# ---------------------------------------------------------------------------

def calculate_rating_quality_score(product_id: str) -> float:
    """Rating distribution health — penalises bimodal, rewards natural skew.

    Returns 0.5 when fewer than 3 reviews are available.
    """
    from apps.reviews.models import Review

    ratings = list(
        Review.objects.filter(product_id=product_id, is_published=True)
        .values_list("rating", flat=True)
    )

    if len(ratings) < 3:
        return 0.5

    arr = np.array(ratings, dtype=float)
    total = len(arr)
    std = float(np.std(arr))

    # Base score: lower std → healthier (max std for 1-5 scale is ~2.0)
    base = _clamp(1.0 - (std / 2.0))

    # Bimodal detection
    count_low = int(np.sum(arr <= 2))
    count_mid = int(np.sum(arr == 3))
    count_high = int(np.sum(arr >= 4))

    pct_low = count_low / total
    pct_mid = count_mid / total
    pct_high = count_high / total

    if pct_low > 0.25 and pct_high > 0.25 and pct_mid < 0.15:
        base *= 0.6  # 40% bimodal penalty

    # Skewness bonus: negative skew (mass on right / high ratings) is healthy
    mean = float(np.mean(arr))
    median = float(np.median(arr))
    # Pearson's second skewness approximation
    skew = (3.0 * (mean - median)) / std if std > 0 else 0.0
    if skew < 0:
        base = min(1.0, base + abs(skew) * 0.05)

    return _clamp(base)


# ---------------------------------------------------------------------------
# Component 3: Price Value Score
# ---------------------------------------------------------------------------

def calculate_price_value_score(product_id: str) -> float:
    """Price-to-quality ratio vs category peers, percentile-ranked.

    Returns 0.5 when there is no price, no category, or fewer than 3 peers.
    """
    from apps.products.models import Product

    try:
        product = Product.objects.select_related("category").get(id=product_id)
    except Product.DoesNotExist:
        return 0.5

    if not product.category or not product.current_best_price:
        return 0.5

    peers = list(
        Product.objects.filter(
            category=product.category,
            status=Product.Status.ACTIVE,
            current_best_price__isnull=False,
        )
        .values_list("id", "current_best_price", "avg_rating")
    )

    if len(peers) < 3:
        return 0.5

    # Value ratio: rating per rupee (higher = better deal)
    def value_ratio(price: Decimal, rating: Decimal | None) -> float:
        r = float(rating) if rating is not None else 3.0
        p = float(price)
        return r / p if p > 0 else 0.0

    ratios = [(pid, value_ratio(price, rating)) for pid, price, rating in peers]
    ratios.sort(key=lambda x: x[1], reverse=True)  # best value first

    # Find this product's rank (0-indexed)
    rank = next(
        (i for i, (pid, _) in enumerate(ratios) if str(pid) == str(product_id)),
        len(ratios) - 1,
    )

    # Percentile score: rank 0 (best) → 1.0, rank N-1 (worst) → ~0.0
    total = len(ratios)
    score = 1.0 - (rank / max(total - 1, 1))

    return _clamp(score)


# ---------------------------------------------------------------------------
# Component 4: Review Credibility Score
# ---------------------------------------------------------------------------

def calculate_review_credibility_score(product_id: str) -> float:
    """Composite credibility from 4 sub-signals.

    Sub-signals and weights:
      - Verified purchase %  (0.35)
      - Review length quality (0.25)
      - Copy-paste uniqueness (0.25)
      - Review burst detection (0.15)

    Returns 0.5 when no published reviews exist.
    """
    from apps.reviews.models import Review

    reviews = Review.objects.filter(product_id=product_id, is_published=True)
    total = reviews.count()

    if total == 0:
        return 0.5

    # A: Verified purchase percentage
    verified = reviews.filter(is_verified_purchase=True).count()
    vp_score = verified / total

    # B: Review length quality
    bodies = list(reviews.exclude(body="").values_list("body", flat=True))
    if not bodies:
        length_score = 0.5
    else:
        quality_count = sum(1 for b in bodies if len(b) >= 50)
        short_count = sum(1 for b in bodies if len(b) < 20)
        length_score = quality_count / len(bodies)
        if len(bodies) > 0 and (short_count / len(bodies)) > 0.40:
            length_score *= 0.5

    # C: Copy-paste uniqueness (via content_hash)
    hashes = list(reviews.exclude(content_hash="").values_list("content_hash", flat=True))
    if len(hashes) < 2:
        copy_score = 1.0
    else:
        unique_hashes = len(set(hashes))
        copy_score = unique_hashes / len(hashes)

    # D: Review burst detection
    review_dates = list(
        reviews.exclude(review_date=None)
        .values_list("review_date", flat=True)
        .order_by("review_date")
    )
    burst_score = 1.0
    burst_window = timedelta(days=ScoringConfig.review_burst_window_days())
    burst_threshold = ScoringConfig.review_burst_fraction()

    if len(review_dates) >= 5:
        max_in_window = 0
        for i, d in enumerate(review_dates):
            window_end = d + burst_window
            count_in_window = sum(1 for rd in review_dates[i:] if rd <= window_end)
            max_in_window = max(max_in_window, count_in_window)

        burst_fraction = max_in_window / len(review_dates)
        if burst_fraction > burst_threshold:
            burst_score = _clamp(1.0 - burst_fraction)

    # Weighted composite
    credibility = (
        0.35 * vp_score +
        0.25 * length_score +
        0.25 * copy_score +
        0.15 * burst_score
    )

    return _clamp(credibility)


# ---------------------------------------------------------------------------
# Component 5: Price Stability Score
# ---------------------------------------------------------------------------

def calculate_price_stability_score(product_id: str) -> float:
    """Price Coefficient of Variation over 90 days.

    Penalises artificial inflation before sales and excessive flash-sale
    frequency.  Returns 0.5 when fewer than 5 snapshots are available.
    """
    from apps.pricing.models import PriceSnapshot

    window_days = ScoringConfig.price_stability_window_days()
    window_start = timezone.now() - timedelta(days=window_days)

    snapshots = list(
        PriceSnapshot.objects.filter(
            product_id=product_id,
            time__gte=window_start,
            in_stock=True,
        )
        .values_list("price", flat=True)
        .order_by("time")
    )

    if len(snapshots) < 5:
        return 0.5

    prices = np.array([float(p) for p in snapshots])
    mean_price = float(np.mean(prices))
    std_price = float(np.std(prices))
    cov = std_price / mean_price if mean_price > 0 else 0.0

    # CoV 0 = perfectly stable (1.0), CoV >= 0.5 = volatile (near 0.0)
    stability_base = _clamp(1.0 - (cov * 2.0))

    # Inflation detection: spike >15% then drop >15% within 7 snapshots
    inflation_penalty = 0.0
    for i in range(1, len(prices)):
        if prices[i] > prices[i - 1] * 1.15:
            future = prices[i + 1:i + 8]
            if len(future) > 0 and float(np.min(future)) < prices[i] * 0.85:
                inflation_penalty = 0.2
                break

    # Flash sale frequency: count significant drops (>15%)
    discount_events = 0
    for i in range(1, len(prices)):
        if prices[i] < prices[i - 1] * 0.85:
            discount_events += 1

    flash_penalty = 0.0
    if discount_events > ScoringConfig.flash_sale_penalty_threshold():
        flash_penalty = min(0.3, discount_events * 0.03)

    score = stability_base - inflation_penalty - flash_penalty
    return _clamp(score)


# ---------------------------------------------------------------------------
# Component 6: Return Signal Score
# ---------------------------------------------------------------------------

def calculate_return_signal_score(product_id: str) -> float:
    """Aggregated return/refund rate from parsed user orders.

    Cold-starts at 0.5 when fewer than 10 data points are available.
    """
    from apps.email_intel.models import ParsedOrder, RefundTracking

    total_orders = ParsedOrder.objects.filter(matched_product_id=product_id).count()

    if total_orders < ScoringConfig.return_signal_min_datapoints():
        return 0.5

    refund_count = RefundTracking.objects.filter(
        order__matched_product_id=product_id,
    ).count()

    return_rate = refund_count / total_orders
    # 0% return → 1.0, 50%+ → 0.0
    score = 1.0 - (return_rate * 2.0)
    return _clamp(score)


# ---------------------------------------------------------------------------
# Fraud Penalty Multiplier
# ---------------------------------------------------------------------------

def calculate_fraud_penalty_multiplier(product_id: str) -> float:
    """Fraud penalty multiplier in [0.5, 1.0].

    Uses ``Review.is_flagged`` as the primary signal.  Until the
    ``detect_fake_reviews`` task populates fraud flags, this will
    typically return 1.0.
    """
    from apps.reviews.models import Review

    reviews = Review.objects.filter(product_id=product_id, is_published=True)
    total = reviews.count()
    if total == 0:
        return 1.0

    flagged = reviews.filter(is_flagged=True).count()
    flagged_pct = flagged / total

    multiplier = 1.0
    if flagged_pct > 0.30:
        multiplier *= 0.7

    return max(0.5, multiplier)


# ---------------------------------------------------------------------------
# Confidence Multiplier
# ---------------------------------------------------------------------------

def calculate_confidence_multiplier(product_id: str) -> tuple[float, str]:
    """Confidence multiplier in [0.6, 1.0] and a human-readable label.

    Tiers (from ARCHITECTURE.md):
      <5 reviews   → 0.6  "Not enough data"
      5-19         → 0.7  "Preliminary"
      20-49        → 0.8  "Moderate"
      50-199       → 0.9  "Good"
      200+         → 1.0  "High"

    Additional reductions:
      - No price history older than 7 days  → -0.1
      - Single marketplace only             → -0.05
    """
    from apps.pricing.models import PriceSnapshot
    from apps.products.models import ProductListing
    from apps.reviews.models import Review

    review_count = Review.objects.filter(
        product_id=product_id, is_published=True
    ).count()

    if review_count < 5:
        multiplier, label = 0.6, "Not enough data"
    elif review_count < 20:
        multiplier, label = 0.7, "Preliminary"
    elif review_count < 50:
        multiplier, label = 0.8, "Moderate"
    elif review_count < 200:
        multiplier, label = 0.9, "Good"
    else:
        multiplier, label = 1.0, "High"

    # Price history depth check
    seven_days_ago = timezone.now() - timedelta(days=7)
    has_old_price = PriceSnapshot.objects.filter(
        product_id=product_id,
        time__lte=seven_days_ago,
    ).exists()
    if not has_old_price:
        multiplier -= 0.1

    # Marketplace breadth check
    marketplace_count = (
        ProductListing.objects.filter(product_id=product_id, in_stock=True)
        .values("marketplace_id")
        .distinct()
        .count()
    )
    if marketplace_count <= 1:
        multiplier -= 0.05

    return (max(0.6, round(multiplier, 2)), label)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

class ComponentResult(NamedTuple):
    """Bundle of all DudScore component outputs."""
    sentiment: float
    rating_quality: float
    price_value: float
    review_credibility: float
    price_stability: float
    return_signal: float
    fraud_multiplier: float
    confidence_multiplier: float
    confidence_label: str


def compute_all_components(product_id: str) -> ComponentResult:
    """Run all six component calculators plus multipliers."""
    sentiment = calculate_sentiment_score(product_id)
    rating_quality = calculate_rating_quality_score(product_id)
    price_value = calculate_price_value_score(product_id)
    review_credibility = calculate_review_credibility_score(product_id)
    price_stability = calculate_price_stability_score(product_id)
    return_signal = calculate_return_signal_score(product_id)
    fraud_multiplier = calculate_fraud_penalty_multiplier(product_id)
    confidence_multiplier, confidence_label = calculate_confidence_multiplier(product_id)

    return ComponentResult(
        sentiment=sentiment,
        rating_quality=rating_quality,
        price_value=price_value,
        review_credibility=review_credibility,
        price_stability=price_stability,
        return_signal=return_signal,
        fraud_multiplier=fraud_multiplier,
        confidence_multiplier=confidence_multiplier,
        confidence_label=confidence_label,
    )
