"""Generic order email parser — best-effort fallback.

Used when no marketplace-specific parser is available. Scans for ₹ amounts,
order ID patterns, and product keywords with lower confidence scores.
"""

from __future__ import annotations

import re
from decimal import Decimal

import structlog

from .base import (
    BaseEmailParser,
    OrderParseResult,
    ParsedItem,
    extract_order_id,
    parse_price,
)

logger = structlog.get_logger(__name__)


class GenericOrderParser(BaseEmailParser):
    """Best-effort parser for unknown or unsupported marketplaces."""

    marketplace = "unknown"

    def __init__(self, email: object, body: str, marketplace: str = "unknown") -> None:
        super().__init__(email, body)
        self.marketplace = marketplace

    def parse_order(self) -> OrderParseResult:
        """Best-effort extraction of order data."""
        order_id = extract_order_id(self.body, self.marketplace)
        product_name = self._extract_product_name()
        price = self.extract_first_price()
        delivery_date = self.extract_date()
        seller = self.extract_seller()

        items: list[ParsedItem] = []
        if product_name:
            items.append(ParsedItem(
                product_name=product_name,
                price=price,
                seller_name=seller,
                delivery_date=delivery_date,
            ))

        # Lower confidence for generic parsing
        confidence = Decimal("0.40")
        if order_id:
            confidence = Decimal("0.55")
        if order_id and product_name and price:
            confidence = Decimal("0.65")

        return OrderParseResult(
            order_id=order_id,
            items=items,
            total_amount=price,
            delivery_date=delivery_date,
            seller_name=seller,
            confidence=confidence,
        )

    def _extract_product_name(self) -> str:
        """Best-effort product name extraction.

        Tries multiple patterns that are common across marketplaces.
        """
        patterns = [
            re.compile(
                r"(?:Item|Product|You ordered|Your order of|Order for)\s*:?\s*(.+?)(?:\n|<br|$)",
                re.I,
            ),
            re.compile(
                r"(?:Order\s*(?:Confirmation|Details))\s*(?:for|:)\s*(.+?)(?:\n|<br|$)",
                re.I,
            ),
        ]
        for pattern in patterns:
            match = pattern.search(self.body)
            if match:
                name = match.group(1).strip()
                # Clean up — remove prices from the name
                name = re.sub(r"(?:₹|Rs\.?|INR)\s*[\d,]+(?:\.\d{1,2})?", "", name).strip()
                if name and len(name) >= 3:
                    return name[:1000]

        # Last resort: use subject line if it contains meaningful content
        subject = self.email.subject
        if subject and len(subject) > 10:
            # Remove common prefixes
            cleaned = re.sub(
                r"^(Order\s*(Confirmed|Placed|#)|Your\s*order)\s*[-:]\s*",
                "",
                subject,
                flags=re.I,
            ).strip()
            if cleaned and len(cleaned) >= 5:
                return cleaned[:1000]

        return ""
