"""Amazon.in order email parser.

Parses HTML email bodies from Amazon.in using BeautifulSoup + nh3 for safety.
Extracts order IDs, product names, prices, delivery dates, and seller info.
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

# Amazon order ID: 123-1234567-1234567
_AMAZON_ORDER_RE = re.compile(r"(\d{3}-\d{7}-\d{7})")

# "Arriving" / "Delivered" date patterns
_ARRIVING_RE = re.compile(
    r"(?:Arriving|Estimated delivery|Delivery by|Arriving by)\s*:?\s*(.+?)(?:\n|<|$)",
    re.I,
)
_DELIVERED_RE = re.compile(
    r"(?:Delivered|Delivered on)\s*:?\s*(.+?)(?:\n|<|$)", re.I
)

# "Sold by" pattern
_SOLD_BY_RE = re.compile(r"Sold\s+by\s*:?\s*(.+?)(?:\n|<|$)", re.I)

# Price near product: ₹ amounts
_PRICE_RE = re.compile(r"(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)", re.I)


class AmazonOrderParser(BaseEmailParser):
    """Parse Amazon.in order confirmation emails."""

    marketplace = "amazon_in"

    def parse_order(self) -> OrderParseResult:
        """Extract order data from Amazon HTML email."""
        # Sanitize HTML before parsing
        safe_html = nh3.clean(self.body)
        soup = BeautifulSoup(safe_html, "html.parser")
        text = soup.get_text(separator="\n", strip=True)

        order_id = self._extract_order_id(text)
        items = self._extract_items(soup, text)
        delivery_date = self._extract_delivery_date(text)
        seller = self._extract_seller(text)
        total = self._extract_total(text, items)

        # Apply delivery date and seller to items that don't have their own
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
        """Extract Amazon order ID (123-1234567-1234567)."""
        match = _AMAZON_ORDER_RE.search(text)
        return match.group(1) if match else ""

    def _extract_items(
        self, soup: BeautifulSoup, text: str
    ) -> list[ParsedItem]:
        """Extract product items from Amazon email HTML.

        Strategy:
        1. Look for <a> tags with /dp/ or /gp/ in href (most reliable)
        2. Look for text after "Items Ordered" section
        3. Fall back to generic product name regex
        """
        items: list[ParsedItem] = []

        # Strategy 1: Find <a> tags linking to product pages
        product_links = soup.find_all(
            "a", href=re.compile(r"/(dp|gp/product)/", re.I)
        )
        seen_names: set[str] = set()

        for link in product_links:
            name = link.get_text(strip=True)
            if not name or len(name) < 3 or name in seen_names:
                continue
            seen_names.add(name)

            # Look for price near this product link
            price = self._find_price_near_element(link, text, name)

            items.append(ParsedItem(
                product_name=name[:1000],
                price=price,
            ))

        # Strategy 2: "Items Ordered" section
        if not items:
            items = self._parse_items_ordered_section(text)

        # Strategy 3: Fall back to generic extraction
        if not items:
            product_name = self.extract_product_name()
            price = self.extract_first_price()
            if product_name:
                items.append(ParsedItem(
                    product_name=product_name,
                    price=price,
                ))

        return items

    def _find_price_near_element(
        self, element: object, full_text: str, product_name: str
    ) -> Decimal | None:
        """Find price closest to a product name in the text."""
        # Find the product name position in text
        pos = full_text.find(product_name)
        if pos == -1:
            return parse_price(full_text)

        # Search in a window around the product name
        window_start = max(0, pos - 200)
        window_end = min(len(full_text), pos + len(product_name) + 500)
        window = full_text[window_start:window_end]

        return parse_price(window)

    def _parse_items_ordered_section(self, text: str) -> list[ParsedItem]:
        """Parse the 'Items Ordered' section in Amazon emails."""
        items: list[ParsedItem] = []
        pattern = re.compile(
            r"Items?\s*Ordered\s*:?\s*\n(.+?)(?:\n\s*\n|Order\s*Total|$)",
            re.I | re.S,
        )
        match = pattern.search(text)
        if not match:
            return items

        section = match.group(1)
        # Each line could be a product
        for line in section.split("\n"):
            line = line.strip()
            if not line or len(line) < 5:
                continue
            # Skip lines that are just prices or quantities
            if re.match(r"^(₹|Rs|INR|Qty|Quantity|\d+\s*x)", line, re.I):
                continue

            price = parse_price(line)
            # Clean product name — remove price from it
            name = _PRICE_RE.sub("", line).strip()
            if name and len(name) >= 3:
                items.append(ParsedItem(product_name=name[:1000], price=price))

        return items

    def _extract_delivery_date(self, text: str) -> object | None:
        """Extract delivery date from 'Arriving' or 'Delivered' patterns."""
        for pattern in (_DELIVERED_RE, _ARRIVING_RE):
            match = pattern.search(text)
            if match:
                date_text = match.group(1).strip()
                dt = parse_date(date_text)
                if dt:
                    return dt
        # Fall back to generic date extraction
        return self.extract_date()

    def _extract_seller(self, text: str) -> str:
        """Extract seller from 'Sold by' text."""
        match = _SOLD_BY_RE.search(text)
        return match.group(1).strip()[:500] if match else ""

    def _extract_total(
        self, text: str, items: list[ParsedItem]
    ) -> Decimal | None:
        """Extract order total — look for 'Order Total' or 'Grand Total'."""
        total_re = re.compile(
            r"(?:Order\s*Total|Grand\s*Total|Total)\s*:?\s*(?:₹|Rs\.?|INR)\s*([\d,]+(?:\.\d{1,2})?)",
            re.I,
        )
        match = total_re.search(text)
        if match:
            try:
                return Decimal(match.group(1).replace(",", ""))
            except Exception:
                pass

        # Fall back: sum of item prices
        item_prices = [i.price for i in items if i.price]
        return sum(item_prices) if item_prices else self.extract_first_price()
