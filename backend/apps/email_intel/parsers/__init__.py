"""Email parser registry — routes emails to marketplace-specific parsers.

Main entry point: parse_email(email_id)

Called by the process_inbound_email Celery task. Each inbound email is:
1. Loaded from DB
2. Decrypted (AES-256-GCM)
3. Marketplace-detected (from sender domain)
4. Categorized (order, shipping, delivery, return, refund, subscription, promo, otp)
5. Parsed into structured records (ParsedOrder, RefundTracking, ReturnWindow, etc.)
6. Post-processed (product matching, affiliate attribution, notifications)
"""

from __future__ import annotations

import re
from datetime import timedelta
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import structlog
from django.utils import timezone

from common.encryption import decrypt

from apps.email_intel.models import (
    DetectedSubscription,
    InboxEmail,
    ParsedOrder,
    RefundTracking,
    ReturnWindow,
)

from .amazon import AmazonOrderParser
from .base import (
    BaseEmailParser,
    OrderParseResult,
    REFUND_AMOUNT_RE,
    RETURN_WINDOW_DAYS,
    categorize_email,
    detect_marketplace,
    extract_order_id,
    parse_date,
    parse_price,
)
from .flipkart import FlipkartOrderParser
from .generic import GenericOrderParser

if TYPE_CHECKING:
    pass

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Parser registry: marketplace slug → parser class
# ---------------------------------------------------------------------------

PARSER_REGISTRY: dict[str, type[BaseEmailParser]] = {
    "amazon_in": AmazonOrderParser,
    "flipkart": FlipkartOrderParser,
}


def get_order_parser(
    marketplace: str, email: InboxEmail, body: str
) -> BaseEmailParser:
    """Return the appropriate parser for a marketplace."""
    parser_cls = PARSER_REGISTRY.get(marketplace)
    if parser_cls:
        return parser_cls(email, body)
    return GenericOrderParser(email, body, marketplace=marketplace)


# ---------------------------------------------------------------------------
# Subscription helpers
# ---------------------------------------------------------------------------

_SERVICE_NAME_RE = re.compile(
    r"(?:subscription|renewal|membership)\s*(?:to|for|of|:)\s*(.+?)(?:\.|,|\n|$)",
    re.I,
)

_BILLING_CYCLE_RE = re.compile(
    r"(monthly|yearly|annual|quarterly|weekly)", re.I
)


def _extract_service_name(subject: str, body: str) -> str:
    """Best-effort extraction of subscription service name."""
    match = _SERVICE_NAME_RE.search(subject)
    if match:
        return match.group(1).strip()[:200]
    match = _SERVICE_NAME_RE.search(body[:1000])
    if match:
        return match.group(1).strip()[:200]
    return ""


def _estimate_next_renewal(billing_cycle: str) -> object | None:
    """Estimate next renewal date from billing cycle."""
    cycle_days = {
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }
    days = cycle_days.get(billing_cycle)
    if days:
        return (timezone.now() + timedelta(days=days)).date()
    return None


# ---------------------------------------------------------------------------
# Category-specific parse handlers
# ---------------------------------------------------------------------------

def _find_existing_order(
    user: object, order_id: str, marketplace: str
) -> ParsedOrder | None:
    """Look up a previously parsed order by order_id + marketplace."""
    if not order_id:
        return None
    return (
        ParsedOrder.objects
        .filter(user=user, order_id=order_id, marketplace=marketplace)
        .first()
    )


def _handle_order(
    email: InboxEmail, body: str, marketplace: str, confidence: Decimal
) -> ParsedOrder | None:
    """Parse order email and create ParsedOrder record(s)."""
    parser = get_order_parser(marketplace, email, body)
    result: OrderParseResult = parser.parse_order()

    if not result.items:
        logger.warning(
            "order_parse_no_items",
            email_id=str(email.id),
            marketplace=marketplace,
        )
        return None

    first_order: ParsedOrder | None = None

    # Create a ParsedOrder for EACH item in the order
    for item in result.items:
        parsed_order = ParsedOrder.objects.create(
            user=email.user,
            source="whydud_email",
            order_id=result.order_id,
            marketplace=marketplace,
            product_name=item.product_name,
            quantity=item.quantity,
            price_paid=item.price,
            total_amount=result.total_amount if len(result.items) == 1 else item.price,
            order_date=email.received_at.date(),
            delivery_date=(
                item.delivery_date.date()
                if item.delivery_date
                else (result.delivery_date.date() if result.delivery_date else None)
            ),
            seller_name=item.seller_name or result.seller_name,
            email_message_id=email.message_id,
            match_confidence=result.confidence,
        )

        # Set up default return window
        _create_return_window(email.user, parsed_order, marketplace)

        if first_order is None:
            first_order = parsed_order

    logger.info(
        "parsed_order_confirmation",
        email_id=str(email.id),
        order_id=result.order_id,
        marketplace=marketplace,
        item_count=len(result.items),
    )
    return first_order


def _handle_shipping(
    email: InboxEmail, body: str, marketplace: str
) -> ParsedOrder | None:
    """Update existing order with shipping info, or create stub."""
    order_id = extract_order_id(body, marketplace)
    delivery_date = parse_date(body)
    existing = _find_existing_order(email.user, order_id, marketplace)

    if existing:
        if delivery_date:
            existing.delivery_date = delivery_date.date()
            existing.save(update_fields=["delivery_date", "updated_at"])
        logger.info(
            "parsed_shipping_update",
            email_id=str(email.id),
            order_id=order_id,
        )
        return existing

    # No existing order — create stub
    parser = get_order_parser(marketplace, email, body)
    product_name = parser.extract_product_name() or "Unknown item"

    return ParsedOrder.objects.create(
        user=email.user,
        source="whydud_email",
        order_id=order_id,
        marketplace=marketplace,
        product_name=product_name,
        delivery_date=delivery_date.date() if delivery_date else None,
        email_message_id=email.message_id,
    )


def _handle_delivery(
    email: InboxEmail, body: str, marketplace: str
) -> ParsedOrder | None:
    """Mark order as delivered."""
    order_id = extract_order_id(body, marketplace)
    existing = _find_existing_order(email.user, order_id, marketplace)

    if existing:
        existing.delivery_date = email.received_at.date()
        existing.save(update_fields=["delivery_date", "updated_at"])
        logger.info(
            "parsed_delivery_confirmation",
            email_id=str(email.id),
            order_id=order_id,
        )
        return existing

    # No prior order — create stub with delivery date
    parser = get_order_parser(marketplace, email, body)
    product_name = parser.extract_product_name() or "Unknown item"

    return ParsedOrder.objects.create(
        user=email.user,
        source="whydud_email",
        order_id=order_id,
        marketplace=marketplace,
        product_name=product_name,
        delivery_date=email.received_at.date(),
        email_message_id=email.message_id,
    )


def _handle_refund(
    email: InboxEmail, body: str, marketplace: str
) -> RefundTracking:
    """Create or update RefundTracking from refund email."""
    order_id = extract_order_id(body, marketplace)
    existing_order = _find_existing_order(email.user, order_id, marketplace)

    amount_match = REFUND_AMOUNT_RE.search(body)
    refund_amount = None
    if amount_match:
        try:
            refund_amount = Decimal(amount_match.group(1).replace(",", ""))
        except InvalidOperation:
            pass

    # Determine status from body
    status = "initiated"
    if re.search(r"(credited|completed|success)", body, re.I):
        status = "completed"
    elif re.search(r"(processing|in progress|being processed)", body, re.I):
        status = "processing"

    refund = RefundTracking.objects.create(
        user=email.user,
        order=existing_order,
        status=status,
        refund_amount=refund_amount,
        initiated_at=email.received_at,
        expected_by=email.received_at + timedelta(days=7),
        completed_at=email.received_at if status == "completed" else None,
        marketplace=marketplace,
    )

    logger.info(
        "parsed_refund",
        email_id=str(email.id),
        refund_id=str(refund.id),
        status=status,
        amount=str(refund_amount),
    )
    return refund


def _handle_return(
    email: InboxEmail, body: str, marketplace: str
) -> RefundTracking:
    """Create RefundTracking for return request."""
    order_id = extract_order_id(body, marketplace)
    existing_order = _find_existing_order(email.user, order_id, marketplace)

    # Try to extract return window end date from body
    return_window_date = parse_date(body)

    refund = RefundTracking.objects.create(
        user=email.user,
        order=existing_order,
        status="return_initiated",
        initiated_at=email.received_at,
        marketplace=marketplace,
    )

    # Create a return window record if we have an order
    if existing_order and return_window_date:
        ReturnWindow.objects.update_or_create(
            user=email.user,
            order=existing_order,
            defaults={"window_end_date": return_window_date.date()},
        )

    logger.info(
        "parsed_return",
        email_id=str(email.id),
        refund_id=str(refund.id),
    )
    return refund


def _handle_subscription(
    email: InboxEmail, body: str, marketplace: str
) -> DetectedSubscription | None:
    """Detect and track subscription/renewal emails."""
    amount = parse_price(body)
    cycle_match = _BILLING_CYCLE_RE.search(body)
    billing_cycle = cycle_match.group(1).lower() if cycle_match else ""

    # Normalise cycle
    if billing_cycle in ("annual", "yearly"):
        billing_cycle = "yearly"

    service_name = _extract_service_name(email.subject, body)
    if not service_name:
        return None

    # Upsert — same user + service_name = update
    sub, created = DetectedSubscription.objects.update_or_create(
        user=email.user,
        service_name=service_name,
        defaults={
            "amount": amount,
            "billing_cycle": billing_cycle,
            "is_active": True,
            "next_renewal": _estimate_next_renewal(billing_cycle),
        },
    )

    logger.info(
        "parsed_subscription",
        email_id=str(email.id),
        service=service_name,
        amount=str(amount),
        created=created,
    )
    return sub


def _create_return_window(
    user: object, order: ParsedOrder, marketplace: str
) -> ReturnWindow | None:
    """Create a return window with marketplace-specific defaults."""
    days = RETURN_WINDOW_DAYS.get(marketplace, 10)
    base_date = order.delivery_date or order.order_date
    if not base_date:
        return None

    return ReturnWindow.objects.create(
        user=user,
        order=order,
        window_end_date=base_date + timedelta(days=days),
    )


# ---------------------------------------------------------------------------
# Main entry point — called by Celery task via services.py
# ---------------------------------------------------------------------------

def parse_email(email_id: str) -> None:
    """Parse an inbound email: detect marketplace, categorize, extract data.

    Args:
        email_id: UUID string of the InboxEmail to process.

    Raises:
        InboxEmail.DoesNotExist: if no email with that ID.
    """
    email = InboxEmail.objects.select_related("user").get(id=email_id)

    if email.parse_status == InboxEmail.ParseStatus.PARSED:
        logger.info("email_already_parsed", email_id=email_id)
        return

    try:
        # Step 1: Decrypt body (prefer HTML for rich parsing, fall back to text)
        body = ""
        if email.body_html_encrypted:
            body = decrypt(bytes(email.body_html_encrypted))
        elif email.body_text_encrypted:
            body = decrypt(bytes(email.body_text_encrypted))

        if not body:
            email.parse_status = InboxEmail.ParseStatus.SKIPPED
            email.save(update_fields=["parse_status"])
            logger.info("email_empty_body_skipped", email_id=email_id)
            return

        # Step 2: Detect marketplace from sender domain
        marketplace = detect_marketplace(email.sender_address)
        email.marketplace = marketplace

        # Step 3: Categorize email
        category, confidence = categorize_email(email.subject, body)
        email.category = category
        email.confidence = confidence

        # Step 4: Parse based on category
        parsed_entity = None
        entity_type = ""

        if category == InboxEmail.Category.ORDER:
            parsed_entity = _handle_order(email, body, marketplace, confidence)
            entity_type = "parsed_order"

        elif category == InboxEmail.Category.SHIPPING:
            parsed_entity = _handle_shipping(email, body, marketplace)
            entity_type = "parsed_order"

        elif category == InboxEmail.Category.DELIVERY:
            parsed_entity = _handle_delivery(email, body, marketplace)
            entity_type = "parsed_order"

        elif category == InboxEmail.Category.REFUND:
            parsed_entity = _handle_refund(email, body, marketplace)
            entity_type = "refund_tracking"

        elif category == InboxEmail.Category.RETURN:
            parsed_entity = _handle_return(email, body, marketplace)
            entity_type = "refund_tracking"

        elif category == InboxEmail.Category.SUBSCRIPTION:
            parsed_entity = _handle_subscription(email, body, marketplace)
            entity_type = "subscription"

        # OTP and PROMO: no structured data to extract, just categorize

        # Step 5: Link parsed entity back to email
        if parsed_entity:
            email.parsed_entity_id = parsed_entity.id
            email.parsed_entity_type = entity_type

        email.parse_status = InboxEmail.ParseStatus.PARSED
        email.save(update_fields=[
            "marketplace",
            "category",
            "confidence",
            "parse_status",
            "parsed_entity_type",
            "parsed_entity_id",
        ])

        logger.info(
            "email_parsed",
            email_id=email_id,
            marketplace=marketplace,
            category=category,
            confidence=str(confidence),
            has_entity=parsed_entity is not None,
        )

        # Step 6: Post-parse processing (product matching, notifications, etc.)
        if parsed_entity and entity_type == "parsed_order":
            from apps.email_intel.services import post_parse_order
            post_parse_order(email, parsed_entity, marketplace)

    except Exception:
        email.parse_status = InboxEmail.ParseStatus.FAILED
        email.save(update_fields=["parse_status"])
        logger.exception("email_parse_failed", email_id=email_id)
        raise
