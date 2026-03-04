"""Deal detection engine.

Scans active products for genuine deals: error pricing, lowest-ever prices,
flash sales, and real discounts. Called periodically by the Celery beat schedule.

Detection Logic:
  1. Scope: only products with a new price snapshot in the last N hours.
  2. Compare current_price against 30-day average, previous-day price,
     and all-time lowest.
  3. Classify into: error_price > lowest_ever > flash_sale > genuine_discount.
  4. Deactivate old deals whose price has recovered.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count, F
from django.utils import timezone

from apps.deals.models import Deal
from apps.pricing.models import PriceSnapshot
from apps.products.models import Product, ProductListing
from common.app_settings import DealDetectionConfig

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_avg_price_30d(listing_id, window_start) -> Decimal | None:
    """Return average price for a listing over the configured window.

    Returns None if fewer than ``DealDetectionConfig.min_snapshots_for_avg``
    snapshots exist in the window.
    """
    result = PriceSnapshot.objects.filter(
        listing_id=listing_id,
        time__gte=window_start,
        in_stock=True,
    ).aggregate(avg_price=Avg("price"), snap_count=Count("time"))
    if result["snap_count"] < DealDetectionConfig.min_snapshots_for_avg():
        return None
    return result["avg_price"]


def _get_previous_day_price(listing_id, now) -> Decimal | None:
    """Return the most recent price snapshot from approximately 24h ago.

    Uses an 18–30 h window to handle irregular scraping schedules.
    """
    yesterday_end = now - timedelta(hours=18)
    yesterday_start = now - timedelta(hours=30)
    return (
        PriceSnapshot.objects.filter(
            listing_id=listing_id,
            time__gte=yesterday_start,
            time__lte=yesterday_end,
            in_stock=True,
        )
        .order_by("-time")
        .values_list("price", flat=True)
        .first()
    )


def _calc_discount_pct(current_price: Decimal, reference_price: Decimal) -> Decimal:
    """Calculate discount percentage: ``(ref - current) / ref * 100``."""
    if not reference_price or reference_price <= 0:
        return Decimal("0.00")
    return ((reference_price - current_price) / reference_price * 100).quantize(
        Decimal("0.01")
    )


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def _classify_deal(
    price: Decimal,
    avg_30d: Decimal | None,
    previous_day_price: Decimal | None,
    lowest_price_ever: Decimal | None,
    error_ratio: Decimal,
    discount_ratio: Decimal,
    overnight_drop_threshold: float,
    flash_sale_drop_threshold: float,
) -> tuple[str | None, str | None, Decimal | None]:
    """Classify a listing's current price into a deal type.

    Returns ``(deal_type, confidence, reference_price)`` or
    ``(None, None, None)`` when no deal is detected.

    Priority order: error_price > lowest_ever > flash_sale > genuine_discount.
    """
    # 1. Error pricing: overnight drop > 40% AND price < 30-day avg * 0.5
    if previous_day_price and previous_day_price > 0 and avg_30d:
        overnight_drop = (previous_day_price - price) / previous_day_price
        if (
            float(overnight_drop) > overnight_drop_threshold
            and price < avg_30d * error_ratio
        ):
            return Deal.DealType.ERROR_PRICE, Deal.Confidence.HIGH, avg_30d

    # 2. Lowest ever: current <= all-time lowest
    if (
        lowest_price_ever is not None
        and lowest_price_ever > 0
        and price <= lowest_price_ever
    ):
        return (
            Deal.DealType.LOWEST_EVER,
            Deal.Confidence.HIGH,
            avg_30d or lowest_price_ever,
        )

    # 3. Flash sale: significant overnight drop (>20%) that didn't qualify
    #    as error pricing — likely a short-lived promotion.
    if previous_day_price and previous_day_price > 0:
        overnight_drop = float(
            (previous_day_price - price) / previous_day_price
        )
        if overnight_drop > flash_sale_drop_threshold:
            return (
                Deal.DealType.FLASH_SALE,
                Deal.Confidence.LOW,
                previous_day_price,
            )

    # 4. Genuine discount: 15 %+ below 30-day avg (price < avg * 0.85)
    if avg_30d and price < avg_30d * discount_ratio:
        return Deal.DealType.GENUINE_DISCOUNT, Deal.Confidence.MEDIUM, avg_30d

    return None, None, None


# ---------------------------------------------------------------------------
# Deactivation
# ---------------------------------------------------------------------------


def _deactivate_stale_deals() -> int:
    """Mark deals as ended when conditions no longer hold.

    Deactivation triggers:
    - Product is no longer active.
    - Listing is out of stock.
    - Listing price has risen back to or above the reference price.
    """
    now = timezone.now()
    count = 0

    # Inactive products.
    stale = Deal.objects.filter(is_active=True).exclude(
        product__status=Product.Status.ACTIVE,
    )
    count += stale.update(is_active=False, ended_at=now)

    # Out-of-stock listings.
    listing_oos = Deal.objects.filter(
        is_active=True,
        listing__isnull=False,
        listing__in_stock=False,
    )
    count += listing_oos.update(is_active=False, ended_at=now)

    # Price recovered — listing price >= reference price.
    price_recovered = Deal.objects.filter(
        is_active=True,
        listing__isnull=False,
        reference_price__isnull=False,
        listing__current_price__gte=F("reference_price"),
    )
    count += price_recovered.update(is_active=False, ended_at=now)

    if count:
        logger.info("deactivated_stale_deals count=%d", count)
    return count


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def detect_deals() -> dict:
    """Scan products with recent price data for genuine deals.

    Only processes products that received a new price snapshot in the
    last ``DealDetectionConfig.recent_snapshot_hours()`` hours to avoid
    redundant work on products with stale data.

    Returns a summary dict with counts of deals found per type.
    """
    now = timezone.now()
    window_days = DealDetectionConfig.avg_price_window_days()
    window_start = now - timedelta(days=window_days)
    recent_hours = DealDetectionConfig.recent_snapshot_hours()
    recent_cutoff = now - timedelta(hours=recent_hours)
    error_ratio = Decimal(str(DealDetectionConfig.error_price_ratio()))
    discount_ratio = Decimal(str(DealDetectionConfig.genuine_discount_ratio()))
    overnight_drop_threshold = DealDetectionConfig.overnight_drop_threshold()
    flash_sale_drop_threshold = DealDetectionConfig.flash_sale_drop_threshold()
    batch_size = DealDetectionConfig.batch_size()

    stats: dict[str, int] = {
        "error_price": 0,
        "lowest_ever": 0,
        "genuine_discount": 0,
        "flash_sale": 0,
        "skipped_zero_price": 0,
        "skipped_insufficient_data": 0,
        "deactivated": 0,
    }

    # Phase 1: deactivate stale deals.
    stats["deactivated"] = _deactivate_stale_deals()

    # Phase 2: narrow scope to products with recent snapshots.
    product_ids_recent = (
        PriceSnapshot.objects.filter(time__gte=recent_cutoff)
        .values("product_id")
        .distinct()
    )

    products_qs = (
        Product.objects.filter(
            id__in=product_ids_recent,
            status=Product.Status.ACTIVE,
        )
        .only("id", "lowest_price_ever")
        .iterator(chunk_size=batch_size)
    )

    for product in products_qs:
        # Edge case: skip products with only 1 snapshot (insufficient data).
        if PriceSnapshot.objects.filter(product_id=product.id).count() < 2:
            stats["skipped_insufficient_data"] += 1
            continue

        listings = (
            ProductListing.objects.filter(product=product, in_stock=True)
            .select_related("marketplace")
            .exclude(current_price__isnull=True)
        )

        best_deal_type: str | None = None
        best_confidence: str | None = None
        best_listing: ProductListing | None = None
        best_reference_price: Decimal | None = None

        for listing in listings:
            price = listing.current_price

            # Edge case: skip ₹0 / negative prices (data errors).
            if not price or price <= 0:
                stats["skipped_zero_price"] += 1
                continue

            avg_30d = _get_avg_price_30d(listing.id, window_start)
            previous_day_price = _get_previous_day_price(listing.id, now)

            deal_type, confidence, reference = _classify_deal(
                price=price,
                avg_30d=avg_30d,
                previous_day_price=previous_day_price,
                lowest_price_ever=product.lowest_price_ever,
                error_ratio=error_ratio,
                discount_ratio=discount_ratio,
                overnight_drop_threshold=overnight_drop_threshold,
                flash_sale_drop_threshold=flash_sale_drop_threshold,
            )

            if deal_type is None:
                continue

            # Keep the best deal across all listings for this product.
            type_priority = {
                Deal.DealType.ERROR_PRICE: 4,
                Deal.DealType.LOWEST_EVER: 3,
                Deal.DealType.FLASH_SALE: 2,
                Deal.DealType.GENUINE_DISCOUNT: 1,
            }
            if best_deal_type is None or type_priority.get(
                deal_type, 0
            ) > type_priority.get(best_deal_type, 0):
                best_deal_type = deal_type
                best_confidence = confidence
                best_listing = listing
                best_reference_price = reference

        if best_deal_type and best_listing and best_confidence:
            reference = best_reference_price or Decimal("0")
            try:
                Deal.objects.update_or_create(
                    product=product,
                    listing=best_listing,
                    is_active=True,
                    defaults={
                        "marketplace": best_listing.marketplace,
                        "deal_type": best_deal_type,
                        "current_price": best_listing.current_price,
                        "reference_price": reference,
                        "discount_pct": _calc_discount_pct(
                            best_listing.current_price, reference
                        ),
                        "confidence": best_confidence,
                        "ended_at": None,
                    },
                )
            except Deal.MultipleObjectsReturned:
                # Race condition: deactivate duplicates and create fresh.
                Deal.objects.filter(
                    product=product, listing=best_listing, is_active=True,
                ).update(is_active=False, ended_at=now)
                Deal.objects.create(
                    product=product,
                    listing=best_listing,
                    is_active=True,
                    marketplace=best_listing.marketplace,
                    deal_type=best_deal_type,
                    current_price=best_listing.current_price,
                    reference_price=reference,
                    discount_pct=_calc_discount_pct(
                        best_listing.current_price, reference
                    ),
                    confidence=best_confidence,
                )
            stats[best_deal_type] = stats.get(best_deal_type, 0) + 1

    logger.info(
        "deal_detection_complete %s",
        " ".join(f"{k}={v}" for k, v in stats.items()),
    )
    return stats
