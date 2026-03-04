"""Flipkart order email parser.

Parses HTML email bodies from Flipkart using BeautifulSoup + nh3 for safety.
Extracts order IDs (OD format), product names, prices, delivery dates.
"""

from __future__ import annotations

import re
from decimal import Decimal

import nh3
import structlog
from bs4 import BeautifulSoup

from .base import (
    BaseEmailParser,
    OrderParseResult,
    ParsedItem,
    parse_date,
    parse_price,
)

logger = structlog.get_logger(__name__)

# Flipkart order ID: OD followed by 15+ digits
_FLIPKART_ORDER_RE = re.compile(r"(OD\d{15,})")

# "Expected delivery" pattern
_EXPECTED_DELIVERY_RE = re.compile(
    r"(?:Expected\s*delivery|Delivery\s*by|Arriving\s*by|Estimated\s*delivery)\s*:?\s*(.+?)(?:\n|<|$)",
    re.I,
)

# Price pattern
_PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I)

# Seller pattern
_SELLER_RE = re.compile(
    r"(?:Sold\s*by|Seller)\s*:?\s*(.+?)(?:\n|<|$)", re.I
)


class FlipkartOrderParser(BaseEmailParser):
    """Parse Flipkart order confirmation emails."""

    marketplace = "flipkart"

    def parse_order(self) -> OrderParseResult:
        """Extract order data from Flipkart HTML email."""
        safe_html = nh3.clean(self.body)
        soup = BeautifulSoup(safe_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        order_id = self._extract_order_id(text)
        items = self._extract_items(soup, text)
        delivery_date = self._extract_delivery_date(text)
        seller = self._extract_seller(text)
        total = self._extract_total(text, items)

        for item in items:
            if not item.delivery_date and delivery_date:
                item.delivery_date = delivery_date
            if not item.seller_name and seller:
                item.seller_name = seller

        return OrderParseResult(
            order_id=order_id,
            items=items,
            total_amount=total,
            delivery_date=delivery_date,
            seller_name=seller,
            confidence=Decimal("0.85") if order_id and items else Decimal("0.60"),
        )

    def _extract_order_id(self, text: str) -> str:
        """Extract Flipkart order ID (OD + digits)."""
        match = _FLIPKART_ORDER_RE.search(text)
        return match.group(1) if match else ""

    def _extract_items(
        self, soup: BeautifulSoup, text: str
    ) -> list[ParsedItem]:
        """Extract product items from Flipkart email HTML.

        Flipkart emails typically have product info in table-based layouts
        or structured div sections.
        """
        items: list[ParsedItem] = []

        # Strategy 1: Look for product links (flipkart.com/*/p/*)
        product_links = soup.find_all(
            "a", href=re.compile(r"flipkart\.com/.+/p/", re.I)
        )
        seen_names: set[str] = set()

        for link in product_links:
            name = link.get_text(strip=True)
            if not name or len(name) < 3 or name in seen_names:
                continue
            seen_names.add(name)

            # Find nearby price
            price = self._find_price_near(text, name)
            items.append(ParsedItem(product_name=name[:1000], price=price))

        # Strategy 2: Look for structured product sections
        if not items:
            items = self._parse_product_sections(text)

        # Strategy 3: Generic fallback
        if not items:
            product_name = self.extract_product_name()
            price = self.extract_first_price()
            if product_name:
                items.append(ParsedItem(
                    product_name=product_name,
                    price=price,
                ))

        return items

    def _find_price_near(self, text: str, product_name: str) -> Decimal | None:
        """Find price closest to a product name."""
        pos = text.find(product_name)
        if pos == -1:
            return parse_price(text)
        window = text[max(0, pos - 200): pos + len(product_name) + 500]
        return parse_price(window)

    def _parse_product_sections(self, text: str) -> list[ParsedItem]:
        """Parse product sections from Flipkart email text."""
        items: list[ParsedItem] = []

        # Flipkart emails often have sections like:
        # Product Name
        # ₹price
        # Qty: N
        lines = text.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Skip short/empty lines and price-only lines
            if not line or len(line) < 5:
                i += 1
                continue

            # Check if this looks like a product name (not a price, not a header)
            if (
                not re.match(r"^(₹|Rs|INR|Qty|Order|Total|Subtotal|Delivery|Shipping)", line, re.I)
                and len(line) > 10
                and not line.startswith("http")
            ):
                # Look ahead for a price
                price = None
                for j in range(i + 1, min(i + 4, len(lines))):
                    price = parse_price(lines[j])
                    if price:
                        break

                if price:
                    items.append(ParsedItem(
                        product_name=line[:1000],
                        price=price,
                    ))
                    i = j + 1
                    continue

            i += 1

        return items

    def _extract_delivery_date(self, text: str) -> object | None:
        """Extract delivery date from Flipkart patterns."""
        match = _EXPECTED_DELIVERY_RE.search(text)
        if match:
            dt = parse_date(match.group(1).strip())
            if dt:
                return dt
        return self.extract_date()

    def _extract_seller(self, text: str) -> str:
        """Extract seller name."""
        match = _SELLER_RE.search(text)
        return match.group(1).strip()[:500] if match else ""

    def _extract_total(
        self, text: str, items: list[ParsedItem]
    ) -> Decimal | None:
        """Extract order total."""
        total_re = re.compile(
            r"(?:Order\s*Total|Total\s*Amount|Grand\s*Total|Amount\s*Payable)\s*:?\s*(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
            re.I,
        )
        match = total_re.search(text)
        if match:
            try:
                return Decimal(match.group(1).replace(",", ""))
            except Exception:
                pass

        item_prices = [i.price for i in items if i.price]
        return sum(item_prices) if item_prices else self.extract_first_price()
