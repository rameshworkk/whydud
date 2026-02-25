"""Celery tasks for pricing app."""
import logging
from decimal import Decimal

from celery import shared_task
from django.db.models import Min
from django.utils import timezone

logger = logging.getLogger(__name__)


def _format_price(paisa: Decimal) -> str:
    """Format paisa value as ₹X,XX,XXX (Indian numbering)."""
    rupees = int(paisa / 100)
    s = str(rupees)
    if len(s) <= 3:
        return f"₹{s}"
    # Indian grouping: last 3 digits, then groups of 2
    last3 = s[-3:]
    rest = s[:-3]
    groups = []
    while rest:
        groups.append(rest[-2:])
        rest = rest[:-2]
    groups.reverse()
    return f"₹{','.join(groups)},{last3}"


@shared_task(queue="alerts")
def check_price_alerts() -> dict:
    """Check all active price alerts and trigger those whose target is met.

    For each active, un-triggered alert:
      1. Find the current best price (marketplace-specific or global)
      2. Update alert.current_price with latest price
      3. If current price <= target price: trigger the alert and send notification

    Returns a summary dict with counts.
    """
    from apps.accounts.tasks import create_notification
    from apps.pricing.models import PriceAlert
    from apps.products.models import ProductListing

    now = timezone.now()
    checked = 0
    triggered = 0
    errors = 0

    active_alerts = (
        PriceAlert.objects
        .filter(is_active=True, is_triggered=False)
        .select_related("product", "marketplace")
    )

    for alert in active_alerts.iterator(chunk_size=500):
        checked += 1
        try:
            # Build query for current best price
            listings_qs = ProductListing.objects.filter(
                product=alert.product,
                in_stock=True,
                current_price__isnull=False,
            )
            if alert.marketplace_id:
                listings_qs = listings_qs.filter(marketplace=alert.marketplace)

            best = listings_qs.aggregate(best_price=Min("current_price"))
            current_price = best["best_price"]

            if current_price is None:
                continue

            # Always update current_price on the alert for tracking
            alert.current_price = current_price
            update_fields = ["current_price", "updated_at"]

            if current_price <= alert.target_price:
                # Find which marketplace has this price
                best_listing = (
                    listings_qs
                    .filter(current_price=current_price)
                    .select_related("marketplace")
                    .first()
                )
                marketplace_name = (
                    best_listing.marketplace.name if best_listing else ""
                )
                marketplace_slug = (
                    best_listing.marketplace.slug if best_listing else ""
                )

                alert.is_triggered = True
                alert.triggered_at = now
                alert.triggered_price = current_price
                alert.triggered_marketplace = marketplace_slug
                alert.notification_sent = True
                alert.is_active = False
                update_fields += [
                    "is_triggered",
                    "triggered_at",
                    "triggered_price",
                    "triggered_marketplace",
                    "notification_sent",
                    "is_active",
                ]

                alert.save(update_fields=update_fields)
                triggered += 1

                # Build notification
                price_display = _format_price(current_price)
                marketplace_suffix = (
                    f" on {marketplace_name}" if marketplace_name else ""
                )

                create_notification.delay(
                    user_id=str(alert.user_id),
                    type="price_alert",
                    title=f"Price alert! {alert.product.title} is now {price_display}{marketplace_suffix}",
                    body=(
                        f"The price dropped to {price_display}, "
                        f"which is at or below your target of {_format_price(alert.target_price)}."
                    ),
                    action_url=f"/product/{alert.product.slug}",
                    action_label="Buy Now",
                    entity_type="product",
                    entity_id=str(alert.product_id),
                    metadata={
                        "alert_id": str(alert.pk),
                        "target_price": str(alert.target_price),
                        "triggered_price": str(current_price),
                        "marketplace": marketplace_slug,
                    },
                )
            else:
                alert.save(update_fields=update_fields)

        except Exception:
            errors += 1
            logger.exception(
                "check_price_alerts: error processing alert %s", alert.pk
            )

    summary = {"checked": checked, "triggered": triggered, "errors": errors}
    if triggered:
        logger.info("check_price_alerts: %s", summary)
    return summary


@shared_task(queue="scraping")
def snapshot_product_prices(product_id: str) -> None:
    """Record current price to price_snapshots hypertable."""
    # TODO Sprint 2 Week 5
    pass
