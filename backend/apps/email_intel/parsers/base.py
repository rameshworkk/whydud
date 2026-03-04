"""Base email parser — shared helpers, marketplace detection, categorization.

All marketplace-specific parsers inherit from BaseEmailParser.
"""

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

import structlog
from django.utils import timezone

if TYPE_CHECKING:
    from apps.email_intel.models import InboxEmail

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
    "bigbasket": ["bigbasket.com"],
    "pharmeasy": ["pharmeasy.in"],
    "lenskart": ["lenskart.com"],
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

# Checked in order — first match wins.  Subject scanned first (most reliable).
_CATEGORY_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # OTP / verification — check early, very distinctive
    (re.compile(r"(OTP|one.?time\s*password|verification\s*code)", re.I), "otp"),
    # Order
    (re.compile(r"order\s*(confirm|placed|received|accepted|#)", re.I), "order"),
    # Delivery (more specific, check before shipping)
    (re.compile(r"(delivered|has been delivered|delivery\s*confirm)", re.I), "delivery"),
    # Shipping
    (re.compile(r"(shipped|dispatched|out for delivery|in transit)", re.I), "shipping"),
    # Return
    (re.compile(r"(return\s*(request|initiated|approved|pickup|accepted)|pickup\s*scheduled)", re.I), "return"),
    # Refund
    (re.compile(r"(refund\s*(initiat|process|credit|complet|success)|amount\s*credited|refund\s*processed)", re.I), "refund"),
    # Subscription
    (re.compile(r"(subscription|renewal|recurring|auto.?renew)", re.I), "subscription"),
    # Promo
    (re.compile(r"(sale|offer|discount|cashback|promo|coupon|deal)", re.I), "promo"),
]


def categorize_email(subject: str, body: str) -> tuple[str, Decimal]:
    """Return (category, confidence) from subject + body content.

    Subject is scanned first (higher confidence), then body text.
    """
    from apps.email_intel.models import InboxEmail

    # Check subject first — most reliable
    for pattern, category in _CATEGORY_PATTERNS:
        if pattern.search(subject):
            return category, Decimal("0.90")

    # Fall back to body (first 2000 chars)
    body_snippet = body[:2000]
    for pattern, category in _CATEGORY_PATTERNS:
        if pattern.search(body_snippet):
            return category, Decimal("0.70")

    return InboxEmail.Category.OTHER, Decimal("0.50")


# ---------------------------------------------------------------------------
# Price / date / regex helpers
# ---------------------------------------------------------------------------

# Matches ₹1,234.56 or Rs. 1234 or INR 1,234.00
PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I)

# Common Indian date formats
DATE_FORMATS = [
    "%d %b %Y",      # 25 Jan 2025
    "%d %B %Y",      # 25 January 2025
    "%d-%m-%Y",      # 25-01-2025
    "%Y-%m-%d",      # 2025-01-25
    "%b %d, %Y",     # Jan 25, 2025
    "%B %d, %Y",     # January 25, 2025
    "%d/%m/%Y",      # 25/01/2025
]

DATE_RE = re.compile(
    r"\d{1,2}[\s/-](?:\w{3,9}|\d{1,2})[\s/-]\d{2,4}"
    r"|(?:\w{3,9})\s+\d{1,2},?\s+\d{4}"
)

PRODUCT_NAME_RE = re.compile(
    r"(?:Item|Product|You ordered|Your order of)\s*:?\s*(.+?)(?:\n|<br|$)", re.I
)

SELLER_RE = re.compile(
    r"(?:Sold by|Seller|Fulfilled by)\s*:?\s*(.+?)(?:\n|<br|$)", re.I
)

REFUND_AMOUNT_RE = re.compile(
    r"(?:refund|credit)\s*(?:of|amount)?\s*(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
    re.I,
)


def parse_price(text: str) -> Decimal | None:
    """Extract first price from text as Decimal in rupees."""
    match = PRICE_RE.search(text)
    if not match:
        return None
    try:
        return Decimal(match.group(1).replace(",", ""))
    except InvalidOperation:
        return None


def parse_all_prices(text: str) -> list[Decimal]:
    """Extract all prices from text."""
    prices = []
    for match in PRICE_RE.finditer(text):
        try:
            prices.append(Decimal(match.group(1).replace(",", "")))
        except InvalidOperation:
            continue
    return prices


def parse_date(text: str) -> datetime | None:
    """Extract first recognisable date from text."""
    match = DATE_RE.search(text)
    if not match:
        return None
    raw = match.group(0).strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue
    return None


# ---------------------------------------------------------------------------
# Order-ID patterns (marketplace-specific + generic fallback)
# ---------------------------------------------------------------------------

ORDER_ID_PATTERNS: dict[str, re.Pattern[str]] = {
    "amazon_in": re.compile(r"(?:Order|order)\s*#?\s*(\d{3}-\d{7}-\d{7})", re.I),
    "flipkart": re.compile(r"(OD\d{15,})", re.I),
    "myntra": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
    "meesho": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
    "croma": re.compile(r"(?:Order\s*(?:ID|No|#))\s*:?\s*(\w{8,20})", re.I),
}

ORDER_ID_GENERIC = re.compile(
    r"(?:Order\s*(?:ID|No|#|Number))\s*:?\s*([\w-]{6,30})", re.I
)


def extract_order_id(body: str, marketplace: str) -> str:
    """Extract order ID using marketplace-specific pattern, then fallback."""
    pattern = ORDER_ID_PATTERNS.get(marketplace, ORDER_ID_GENERIC)
    match = pattern.search(body)
    if match:
        return match.group(1).strip()
    # Fallback to generic if marketplace-specific didn't match
    if marketplace in ORDER_ID_PATTERNS:
        match = ORDER_ID_GENERIC.search(body)
        if match:
            return match.group(1).strip()
    return ""


# ---------------------------------------------------------------------------
# Return window defaults per marketplace
# ---------------------------------------------------------------------------

RETURN_WINDOW_DAYS: dict[str, int] = {
    "amazon_in": 10,
    "flipkart": 10,
    "myntra": 30,
    "ajio": 30,
    "meesho": 7,
    "croma": 10,
    "reliance_digital": 10,
    "nykaa": 15,
    "snapdeal": 7,
}


# ---------------------------------------------------------------------------
# Parse result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ParsedItem:
    """A single item extracted from an order email."""

    product_name: str
    price: Decimal | None = None
    quantity: int = 1
    seller_name: str = ""
    delivery_date: datetime | None = None


@dataclass
class OrderParseResult:
    """Result from an order parser."""

    order_id: str = ""
    items: list[ParsedItem] | None = None
    total_amount: Decimal | None = None
    delivery_date: datetime | None = None
    seller_name: str = ""
    confidence: Decimal = Decimal("0.50")

    def __post_init__(self) -> None:
        if self.items is None:
            self.items = []


# ---------------------------------------------------------------------------
# Base parser class
# ---------------------------------------------------------------------------

class BaseEmailParser(ABC):
    """Abstract base for marketplace-specific email parsers."""

    marketplace: str = ""

    def __init__(self, email: InboxEmail, body: str) -> None:
        self.email = email
        self.body = body

    @abstractmethod
    def parse_order(self) -> OrderParseResult:
        """Parse order confirmation email and return structured data."""

    def extract_order_id(self) -> str:
        """Extract order ID from body."""
        return extract_order_id(self.body, self.marketplace)

    def extract_first_price(self) -> Decimal | None:
        return parse_price(self.body)

    def extract_all_prices(self) -> list[Decimal]:
        return parse_all_prices(self.body)

    def extract_date(self) -> datetime | None:
        return parse_date(self.body)

    def extract_product_name(self) -> str:
        match = PRODUCT_NAME_RE.search(self.body)
        return match.group(1).strip()[:1000] if match else ""

    def extract_seller(self) -> str:
        match = SELLER_RE.search(self.body)
        return match.group(1).strip()[:500] if match else ""
