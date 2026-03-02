"""Deal detection engine.

Scans active products for genuine deals: error pricing, lowest-ever prices,
and real discounts. Called periodically by the Celery beat schedule.
"""
import logging
from datetime import timedelta
from decimal import Decimal

from django.db.models import Avg, Count
from django.utils import timezone

from apps.deals.models import Deal
from apps.pricing.models import PriceSnapshot
from apps.products.models import Product, ProductListing
from common.app_settings import DealDetectionConfig

logger = logging.getLogger(__name__)


def _get_avg_price_30d(listing_id: str, window_start) -> Decimal | None:
    """Return average price for a listing over the configured window.

    Returns None if fewer than ``DealDetectionConfig.min_snapshots_for_avg``
    snapshots exist in the window.
    """
    result = (
        PriceSnapshot.objects.filter(
            listing_id=listing_id,
            time__gte=window_start,
            in_stock=True,
        )
        .aggregate(avg_price=Avg("price"), snap_count=Count("id"))
    )
    if result["snap_count"] < DealDetectionConfig.min_snapshots_for_avg():
        return None
    return result["avg_price"]


def _calc_discount_pct(current_price: Decimal, reference_price: Decimal) -> Decimal:
    """Calculate discount percentage: ``(ref - current) / ref * 100``."""
    if not reference_price or reference_price <= 0:
        return Decimal("0.00")
    return ((reference_price - current_price) / reference_price * 100).quantize(
        Decimal("0.01")
    )


def _map_confidence(deal_type: str) -> str:
    """Map deal type to a Deal.Confidence value."""
    if deal_type in ("error_price", "lowest_ever"):
        return Deal.Confidence.HIGH
    return Deal.Confidence.MEDIUM


def _deactivate_stale_deals() -> int:
    """Mark deals as ended when their listing is no longer in stock or
    the product is no longer active."""
    now = timezone.now()
    stale = Deal.objects.filter(is_active=True).exclude(
        product__status=Product.Status.ACTIVE,
    )
    count = stale.update(is_active=False, ended_at=now)

    # Also deactivate deals whose listing went out of stock.
    listing_stale = Deal.objects.filter(
        is_active=True,
        listing__isnull=False,
        listing__in_stock=False,
    )
    count += listing_stale.update(is_active=False, ended_at=now)

    if count:
        logger.info("Deactivated %d stale deals", count)
    return count


def detect_deals() -> dict:
    """Scan active products for genuine deals.

    Returns a summary dict with counts of deals found per type.
    """
    now = timezone.now()
    window_days = DealDetectionConfig.avg_price_window_days()
    window_start = now - timedelta(days=window_days)
    error_ratio = Decimal(str(DealDetectionConfig.error_price_ratio()))
    discount_ratio = Decimal(str(DealDetectionConfig.genuine_discount_ratio()))
    batch_size = DealDetectionConfig.batch_size()

    stats: dict[str, int] = {
        "error_price": 0,
        "lowest_ever": 0,
        "genuine_discount": 0,
        "deactivated": 0,
    }

    # Phase 1: deactivate stale deals.
    stats["deactivated"] = _deactivate_stale_deals()

    # Phase 2: scan active products in batches.
    products_qs = (
        Product.objects.filter(status=Product.Status.ACTIVE)
        .only("id", "lowest_price_ever")
        .iterator(chunk_size=batch_size)
    )

    for product in products_qs:
        listings = (
            ProductListing.objects.filter(product=product, in_stock=True)
            .select_related("marketplace")
            .exclude(current_price__isnull=True)
        )

        best_deal_type: str | None = None
        best_listing: ProductListing | None = None
        best_reference_price: Decimal | None = None

        for listing in listings:
            deal_type = None
            price = listing.current_price

            # 1. Error pricing: price < threshold of 30-day avg.
            avg_30d = _get_avg_price_30d(listing.id, window_start)
            if avg_30d and price < avg_30d * error_ratio:
                deal_type = Deal.DealType.ERROR_PRICE
            # 2. Lowest ever.
            elif (
                product.lowest_price_ever is not None
                and price <= product.lowest_price_ever
            ):
                deal_type = Deal.DealType.LOWEST_EVER
            # 3. Genuine discount: price below threshold of MRP.
            elif listing.mrp and price < listing.mrp * discount_ratio:
                deal_type = Deal.DealType.GENUINE_DISCOUNT

            if deal_type is None:
                continue

            # Keep the best deal across all listings for this product.
            # Priority: error_price > lowest_ever > genuine_discount.
            type_priority = {
                Deal.DealType.ERROR_PRICE: 3,
                Deal.DealType.LOWEST_EVER: 2,
                Deal.DealType.GENUINE_DISCOUNT: 1,
            }
            if best_deal_type is None or type_priority.get(
                deal_type, 0
            ) > type_priority.get(best_deal_type, 0):
                best_deal_type = deal_type
                best_listing = listing
                best_reference_price = avg_30d or listing.mrp

        if best_deal_type and best_listing:
            reference = best_reference_price or Decimal("0")
            Deal.objects.update_or_create(
                product=product,
                listing=best_listing,
                defaults={
                    "marketplace": best_listing.marketplace,
                    "deal_type": best_deal_type,
                    "current_price": best_listing.current_price,
                    "reference_price": reference,
                    "discount_pct": _calc_discount_pct(
                        best_listing.current_price, reference
                    ),
                    "confidence": _map_confidence(best_deal_type),
                    "is_active": True,
                    "ended_at": None,
                },
            )
            stats[best_deal_type] = stats.get(best_deal_type, 0) + 1

    logger.info(
        "Deal detection complete: %s",
        ", ".join(f"{k}={v}" for k, v in stats.items()),
    )
    return stats
