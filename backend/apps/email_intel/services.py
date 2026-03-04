"""Email parsing service — post-parse processing.

After an email is parsed and structured data extracted, this service handles:
1. Fuzzy matching product_name against the product catalog
2. Affiliate click attribution (link purchase to prior affiliate click)
3. User notification creation
4. Return window alert scheduling
"""

from __future__ import annotations

from datetime import timedelta
from difflib import SequenceMatcher

import structlog
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import Notification
from apps.email_intel.models import InboxEmail, ParsedOrder

logger = structlog.get_logger(__name__)


def post_parse_order(
    email: InboxEmail,
    order: ParsedOrder,
    marketplace: str,
) -> None:
    """Run post-parse processing for a parsed order.

    Called after parse_email() successfully creates a ParsedOrder.
    """
    # 1. Match product to catalog
    _match_product_to_catalog(order)

    # 2. Check affiliate click attribution
    _check_affiliate_attribution(order)

    # 3. Create notification
    _create_order_notification(email.user, order, marketplace)

    # 4. Increment WhydudEmail orders counter
    _increment_order_counter(email)

    # 5. Schedule return window alerts if applicable
    _schedule_return_window_alerts(order)


def _match_product_to_catalog(order: ParsedOrder) -> None:
    """Fuzzy match product_name against products.Product.title.

    Uses SequenceMatcher for string similarity. If match confidence > 0.7,
    links the parsed order to the matched product.
    """
    from apps.products.models import Product

    if not order.product_name or order.matched_product_id:
        return

    product_name_lower = order.product_name.lower()

    # Query candidates: search by keywords from the product name
    # Take first 3 significant words for the DB query
    words = [w for w in product_name_lower.split() if len(w) > 2][:3]
    if not words:
        return

    q_filter = Q()
    for word in words:
        q_filter &= Q(title__icontains=word)

    candidates = (
        Product.objects
        .filter(q_filter, status="active")
        .only("id", "title", "slug")[:20]
    )

    best_match = None
    best_ratio = 0.0

    for product in candidates:
        ratio = SequenceMatcher(
            None, product_name_lower, product.title.lower()
        ).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = product

    if best_match and best_ratio > 0.7:
        order.matched_product = best_match
        order.match_confidence = round(best_ratio, 2)
        order.match_status = "matched"
        order.save(update_fields=[
            "matched_product", "match_confidence", "match_status", "updated_at",
        ])
        logger.info(
            "product_matched",
            order_id=str(order.id),
            product_id=str(best_match.id),
            confidence=best_ratio,
        )
    else:
        order.match_status = "unmatched"
        order.save(update_fields=["match_status", "updated_at"])


def _check_affiliate_attribution(order: ParsedOrder) -> None:
    """Check for affiliate click attribution.

    Find recent click_events (within 7 days) for this user + matched product.
    If match: set click_event.purchase_confirmed = True, confirmed_at = now()
    """
    from apps.pricing.models import ClickEvent

    if not order.matched_product_id or not order.user_id:
        return

    seven_days_ago = timezone.now() - timedelta(days=7)

    # Find the most recent unconfirmed click for this user + product
    click = (
        ClickEvent.objects
        .filter(
            user=order.user,
            product=order.matched_product,
            purchase_confirmed=False,
            clicked_at__gte=seven_days_ago,
        )
        .order_by("-clicked_at")
        .first()
    )

    if click:
        click.purchase_confirmed = True
        click.confirmation_source = "email_parsed"
        click.confirmed_at = timezone.now()
        click.save(update_fields=[
            "purchase_confirmed", "confirmation_source", "confirmed_at",
        ])
        logger.info(
            "affiliate_click_attributed",
            click_id=click.id,
            order_id=str(order.id),
            product_id=str(order.matched_product_id),
        )


def _create_order_notification(
    user: object, order: ParsedOrder, marketplace: str
) -> None:
    """Create notification: 'Order detected: {product_name} from {marketplace}'."""
    marketplace_display = marketplace.replace("_", " ").title()

    Notification.objects.create(
        user=user,
        type=Notification.Type.ORDER_DETECTED,
        title=f"Order detected: {order.product_name[:100]}",
        body=f"We detected an order from {marketplace_display}."
        + (f" Order ID: {order.order_id}" if order.order_id else ""),
        action_url="/purchases",
        action_label="View Purchases",
        entity_type="parsed_order",
        entity_id=str(order.id),
        metadata={
            "marketplace": marketplace,
            "order_id": order.order_id,
            "product_name": order.product_name[:200],
        },
    )


def _increment_order_counter(email: InboxEmail) -> None:
    """Increment WhydudEmail.total_orders_detected counter."""
    if email.whydud_email_id:
        from apps.accounts.models import WhydudEmail

        WhydudEmail.objects.filter(id=email.whydud_email_id).update(
            total_orders_detected=models.F("total_orders_detected") + 1
        )


def _schedule_return_window_alerts(order: ParsedOrder) -> None:
    """Schedule Celery tasks for return window alerts (3-day and 1-day).

    Checks if a ReturnWindow exists for this order and schedules
    the alert tasks at the appropriate times.
    """
    from apps.email_intel.models import ReturnWindow

    try:
        return_window = ReturnWindow.objects.get(order=order)
    except ReturnWindow.DoesNotExist:
        return

    now = timezone.now().date()
    end_date = return_window.window_end_date

    if end_date <= now:
        return

    # Schedule 3-day alert
    three_day_alert_date = end_date - timedelta(days=3)
    if three_day_alert_date > now:
        from apps.email_intel.tasks import send_return_window_alert

        eta = timezone.make_aware(
            timezone.datetime.combine(three_day_alert_date, timezone.datetime.min.time())
        )
        send_return_window_alert.apply_async(
            args=[str(return_window.id), 3],
            eta=eta,
        )

    # Schedule 1-day alert
    one_day_alert_date = end_date - timedelta(days=1)
    if one_day_alert_date > now:
        from apps.email_intel.tasks import send_return_window_alert

        eta = timezone.make_aware(
            timezone.datetime.combine(one_day_alert_date, timezone.datetime.min.time())
        )
        send_return_window_alert.apply_async(
            args=[str(return_window.id), 1],
            eta=eta,
        )
