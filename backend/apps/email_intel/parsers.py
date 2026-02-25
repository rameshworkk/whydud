"""Email parsing pipeline — categorize inbound emails and extract structured data.

Called by the process_inbound_email Celery task. Each inbound email is:
1. Decrypted
2. Marketplace-detected (from sender domain)
3. Categorized (order, shipping, delivery, return, refund, subscription, promo)
4. Parsed into structured records (ParsedOrder, RefundTracking, ReturnWindow, etc.)
"""
import re
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

import structlog
from django.utils import timezone

from common.encryption import decrypt

from .models import (
    DetectedSubscription,
    InboxEmail,
    ParsedOrder,
    RefundTracking,
    ReturnWindow,
)

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Marketplace detection
# ---------------------------------------------------------------------------

# sender domain fragment → marketplace slug
MARKETPLACE_SENDERS: dict[str, list[str]] = {
    "amazon_in": ["amazon.in", "amazon.com"],
    "flipkart": ["flipkart.com"],
    "myntra": ["myntra.com"],
    "croma": ["croma.com"],
    "reliance_digital": ["reliancedigital.in"],
    "meesho": ["meesho.com"],
    "ajio": ["ajio.com"],
    "tatacliq": ["tatacliq.com"],
    "jiomart": ["jiomart.com"],
    "nykaa": ["nykaa.com"],
    "snapdeal": ["snapdeal.com"],
}


def detect_marketplace(sender: str) -> str:
    """Return marketplace slug from sender email domain."""
    sender_lower = sender.lower()
    for slug, domains in MARKETPLACE_SENDERS.items():
        if any(d in sender_lower for d in domains):
            return slug
    return "unknown"


# ---------------------------------------------------------------------------
# Category detection
# ---------------------------------------------------------------------------

# (regex pattern on subject+body, category)
# Checked in order — first match wins.
_CATEGORY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"order\s*(confirm|placed|received|accepted)", re.I), "order"),
    (re.compile(r"(shipped|dispatched|out for delivery|in transit)", re.I), "shipping"),
    (re.compile(r"(delivered|delivery confirm|has been delivered)", re.I), "shipping"),
    (re.compile(r"(return\s*(request|initiated|approved|pickup|accepted))", re.I), "return"),
    (re.compile(r"(refund\s*(initiat|process|credit|complet|success))", re.I), "refund"),
    (re.compile(r"(subscription|renewal|recurring|auto.?renew)", re.I), "subscription"),
    (re.compile(r"(offer|deal|sale|coupon|discount|cashback|promo)", re.I), "promo"),
]

# Delivery gets its own pass — must distinguish from generic shipping
_DELIVERY_PATTERN = re.compile(
    r"(delivered|delivery confirm|has been delivered)", re.I
)


def categorize_email(subject: str, body: str) -> str:
    """Return InboxEmail.Category value from subject + body content."""
    text = f"{subject}\n{body[:2000]}"

    # Delivery check first (more specific than shipping)
    if _DELIVERY_PATTERN.search(text):
        # Verify it's not just mentioning estimated delivery
        if not re.search(r"(estimated|expected)\s+delivery", text, re.I):
            return InboxEmail.Category.SHIPPING  # model lumps delivery into shipping

    for pattern, category in _CATEGORY_PATTERNS:
        if pattern.search(text):
            return category

    return InboxEmail.Category.OTHER


# ---------------------------------------------------------------------------
# Price / date helpers
# ---------------------------------------------------------------------------

# Matches ₹1,234.56 or Rs. 1234 or INR 1,234.00
_PRICE_RE = re.compile(
    r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I
)

# Common Indian date formats: 25 Jan 2025, 25-01-2025, 2025-01-25, Jan 25, 2025
_DATE_FORMATS = [
    "%d %b %Y",      # 25 Jan 2025
    "%d %B %Y",      # 25 January 2025
    "%d-%m-%Y",      # 25-01-2025
    "%Y-%m-%d",      # 2025-01-25
    "%b %d, %Y",     # Jan 25, 2025
    "%B %d, %Y",     # January 25, 2025
    "%d/%m/%Y",      # 25/01/2025
]

_DATE_RE = re.compile(
    r"\d{1,2}[\s/-](?:\w{3,9}|\d{1,2})[\s/-]\d{2,4}"
    r"|(?:\w{3,9})\s+\d{1,2},?\s+\d{4}"
)


def _parse_price(text: str) -> Decimal | None:
    """Extract first price from text as Decimal in rupees."""
    match = _PRICE_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def _parse_date(text: str) -> datetime | None:
    """Extract first recognisable date from text."""
    match = _DATE_RE.search(text)
    if not match:
        return None
    raw = match.group(0).strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Marketplace-specific order ID patterns
# ---------------------------------------------------------------------------

_ORDER_ID_PATTERNS: dict[str, re.Pattern] = {
    "amazon_in": re.compile(r"(?:Order|order)\s*#?\s*([\d-]{10,25})", re.I),
    "flipkart": re.compile(r"(?:Order\s*ID|OD)\s*:?\s*(\w{10,25})", re.I),
    "myntra": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
    "meesho": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
    "croma": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
}

# Generic fallback
_ORDER_ID_GENERIC = re.compile(
    r"(?:Order\s*(?:ID|No|#|Number))\s*:?\s*([\w-]{6,30})", re.I
)

_PRODUCT_NAME_RE = re.compile(
    r"(?:Item|Product|You ordered|Your order of)\s*:?\s*(.+?)(?:\n|<br|$)", re.I
)

_SELLER_RE = re.compile(
    r"(?:Sold by|Seller|Fulfilled by)\s*:?\s*(.+?)(?:\n|<br|$)", re.I
)

_TRACKING_RE = re.compile(
    r"(?:Tracking\s*(?:ID|No|Number|#))\s*:?\s*([\w-]{6,30})", re.I
)

_REFUND_AMOUNT_RE = re.compile(
    r"(?:refund|credit)\s*(?:of|amount)?\s*(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)

_RETURN_WINDOW_RE = re.compile(
    r"(?:return|exchange)\s*(?:by|before|within|window)\s*:?\s*(.+?)(?:\.|$)", re.I
)

_SUBSCRIPTION_AMOUNT_RE = _PRICE_RE  # reuse

_BILLING_CYCLE_RE = re.compile(
    r"(monthly|yearly|annual|quarterly|weekly)", re.I
)


# ---------------------------------------------------------------------------
# Category-specific parsers
# ---------------------------------------------------------------------------

def _extract_order_id(body: str, marketplace: str) -> str:
    """Extract order ID using marketplace-specific pattern, then fallback."""
    pattern = _ORDER_ID_PATTERNS.get(marketplace, _ORDER_ID_GENERIC)
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    # Fallback to generic
    if marketplace in _ORDER_ID_PATTERNS:
        match = _ORDER_ID_GENERIC.search(body)
        if match:
            return match.group(1).strip()
    return ""


def parse_order_confirmation(
    email: InboxEmail, body: str, marketplace: str
) -> ParsedOrder | None:
    """Extract order data and create ParsedOrder record."""
    order_id = _extract_order_id(body, marketplace)

    product_match = _PRODUCT_NAME_RE.search(body)
    product_name = product_match.group(1).strip()[:1000] if product_match else "Unknown item"

    price = _parse_price(body)
    delivery_date = _parse_date(body)

    seller_match = _SELLER_RE.search(body)
    seller_name = seller_match.group(1).strip()[:500] if seller_match else ""

    parsed_order = ParsedOrder.objects.create(
        user=email.user,
        source=f"email:{marketplace}",
        order_id=order_id,
        marketplace=marketplace,
        product_name=product_name,
        price_paid=price,
        total_amount=price,
        order_date=email.received_at.date(),
        delivery_date=delivery_date.date() if delivery_date else None,
        seller_name=seller_name,
        email_message_id=email.message_id,
    )

    # Set up default return window (marketplace-specific defaults)
    _create_default_return_window(email.user, parsed_order, marketplace)

    logger.info(
        "parsed_order_confirmation",
        email_id=str(email.id),
        order_id=order_id,
        marketplace=marketplace,
        price=str(price),
    )
    return parsed_order


def parse_shipping_update(
    email: InboxEmail, body: str, marketplace: str
) -> ParsedOrder | None:
    """Update existing order with shipping/delivery info, or create stub."""
    order_id = _extract_order_id(body, marketplace)
    delivery_date = _parse_date(body)

    # Try to find existing order
    existing = _find_existing_order(email.user, order_id, marketplace)

    if existing:
        if delivery_date:
            existing.delivery_date = delivery_date.date()
            existing.save(update_fields=["delivery_date", "updated_at"])
        logger.info(
            "parsed_shipping_update",
            email_id=str(email.id),
            order_id=order_id,
            updated=True,
        )
        return existing

    # No existing order — create a stub
    product_match = _PRODUCT_NAME_RE.search(body)
    product_name = product_match.group(1).strip()[:1000] if product_match else "Unknown item"

    parsed_order = ParsedOrder.objects.create(
        user=email.user,
        source=f"email:{marketplace}",
        order_id=order_id,
        marketplace=marketplace,
        product_name=product_name,
        delivery_date=delivery_date.date() if delivery_date else None,
        email_message_id=email.message_id,
    )

    logger.info(
        "parsed_shipping_stub",
        email_id=str(email.id),
        order_id=order_id,
        marketplace=marketplace,
    )
    return parsed_order


def parse_delivery_confirmation(
    email: InboxEmail, body: str, marketplace: str
) -> ParsedOrder | None:
    """Mark order as delivered."""
    order_id = _extract_order_id(body, marketplace)
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

    # No prior order record — create stub with delivery date
    product_match = _PRODUCT_NAME_RE.search(body)
    product_name = product_match.group(1).strip()[:1000] if product_match else "Unknown item"

    parsed_order = ParsedOrder.objects.create(
        user=email.user,
        source=f"email:{marketplace}",
        order_id=order_id,
        marketplace=marketplace,
        product_name=product_name,
        delivery_date=email.received_at.date(),
        email_message_id=email.message_id,
    )
    return parsed_order


def parse_return_refund(
    email: InboxEmail, body: str, marketplace: str, category: str
) -> RefundTracking | None:
    """Parse return/refund emails and create tracking records."""
    order_id = _extract_order_id(body, marketplace)
    existing_order = _find_existing_order(email.user, order_id, marketplace)

    if category == InboxEmail.Category.REFUND:
        return _parse_refund(email, body, marketplace, existing_order)
    else:
        return _parse_return(email, body, marketplace, existing_order)


def _parse_refund(
    email: InboxEmail,
    body: str,
    marketplace: str,
    order: ParsedOrder | None,
) -> RefundTracking:
    """Create or update RefundTracking from refund email."""
    amount_match = _REFUND_AMOUNT_RE.search(body)
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
        order=order,
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


def _parse_return(
    email: InboxEmail,
    body: str,
    marketplace: str,
    order: ParsedOrder | None,
) -> RefundTracking:
    """Create RefundTracking for return request."""
    refund = RefundTracking.objects.create(
        user=email.user,
        order=order,
        status="return_initiated",
        initiated_at=email.received_at,
        marketplace=marketplace,
    )

    logger.info(
        "parsed_return",
        email_id=str(email.id),
        refund_id=str(refund.id),
    )
    return refund


def parse_subscription(
    email: InboxEmail, body: str, marketplace: str
) -> DetectedSubscription | None:
    """Detect and track subscription/renewal emails."""
    amount = _parse_price(body)
    cycle_match = _BILLING_CYCLE_RE.search(body)
    billing_cycle = cycle_match.group(1).lower() if cycle_match else ""

    # Normalise cycle
    if billing_cycle in ("annual", "yearly"):
        billing_cycle = "yearly"

    # Try to extract service name from subject or body
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _find_existing_order(user, order_id: str, marketplace: str) -> ParsedOrder | None:
    """Look up a previously parsed order by order_id + marketplace."""
    if not order_id:
        return None
    return (
        ParsedOrder.objects
        .filter(user=user, order_id=order_id, marketplace=marketplace)
        .first()
    )


# Default return window days per marketplace
_RETURN_WINDOW_DAYS: dict[str, int] = {
    "amazon_in": 10,
    "flipkart": 10,
    "myntra": 30,
    "ajio": 30,
    "meesho": 7,
    "croma": 10,
    "reliance_digital": 10,
}


def _create_default_return_window(
    user, order: ParsedOrder, marketplace: str
) -> ReturnWindow | None:
    """Create a return window with marketplace-specific defaults."""
    days = _RETURN_WINDOW_DAYS.get(marketplace, 10)
    base_date = order.delivery_date or order.order_date
    if not base_date:
        return None

    return ReturnWindow.objects.create(
        user=user,
        order=order,
        window_end_date=base_date + timedelta(days=days),
    )


_SERVICE_NAME_RE = re.compile(
    r"(?:subscription|renewal|membership)\s*(?:to|for|of|:)\s*(.+?)(?:\.|,|\n|$)",
    re.I,
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


def _estimate_next_renewal(billing_cycle: str) -> datetime | None:
    """Estimate next renewal date from billing cycle."""
    now = timezone.now()
    cycle_days = {
        "weekly": 7,
        "monthly": 30,
        "quarterly": 90,
        "yearly": 365,
    }
    days = cycle_days.get(billing_cycle)
    if days:
        return (now + timedelta(days=days)).date()
    return None


# ---------------------------------------------------------------------------
# Main entry point — called by Celery task
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
        # Decrypt body (prefer text, fall back to HTML)
        body = ""
        if email.body_text_encrypted:
            body = decrypt(bytes(email.body_text_encrypted))
        elif email.body_html_encrypted:
            body = decrypt(bytes(email.body_html_encrypted))

        if not body:
            email.parse_status = InboxEmail.ParseStatus.SKIPPED
            email.save(update_fields=["parse_status"])
            logger.info("email_empty_body_skipped", email_id=email_id)
            return

        # Step 1: Detect marketplace
        marketplace = detect_marketplace(email.sender_address)
        email.marketplace = marketplace

        # Step 2: Categorize
        category = categorize_email(email.subject, body)
        email.category = category

        # Step 3: Parse based on category
        parsed_entity = None

        if category == InboxEmail.Category.ORDER:
            parsed_entity = parse_order_confirmation(email, body, marketplace)
            email.parsed_entity_type = "parsed_order"

        elif category == InboxEmail.Category.SHIPPING:
            parsed_entity = parse_shipping_update(email, body, marketplace)
            email.parsed_entity_type = "parsed_order"

        elif category == InboxEmail.Category.REFUND:
            parsed_entity = parse_return_refund(email, body, marketplace, category)
            email.parsed_entity_type = "refund_tracking"

        elif category == InboxEmail.Category.RETURN:
            parsed_entity = parse_return_refund(email, body, marketplace, category)
            email.parsed_entity_type = "refund_tracking"

        elif category == InboxEmail.Category.SUBSCRIPTION:
            parsed_entity = parse_subscription(email, body, marketplace)
            email.parsed_entity_type = "subscription"

        # Link parsed entity back to email
        if parsed_entity:
            email.parsed_entity_id = parsed_entity.id

        email.parse_status = InboxEmail.ParseStatus.PARSED
        email.save(update_fields=[
            "marketplace",
            "category",
            "parse_status",
            "parsed_entity_type",
            "parsed_entity_id",
        ])

        logger.info(
            "email_parsed",
            email_id=email_id,
            marketplace=marketplace,
            category=category,
            has_entity=parsed_entity is not None,
        )

    except Exception:
        email.parse_status = InboxEmail.ParseStatus.FAILED
        email.save(update_fields=["parse_status"])
        logger.exception("email_parse_failed", email_id=email_id)
        raise
