"""Conversion utilities for backfill data normalization.

All external sources (BuyHatke, PriceHistory.app) return prices in raw INR
and timestamps in IST. Our system uses paisa (Decimal 12,2) and UTC.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
UTC = timezone.utc

# Reasonable price range: ₹0.01 to ₹10 crore (in paisa)
_MIN_PRICE_PAISA = Decimal("1")
_MAX_PRICE_PAISA = Decimal("10000000000")  # 10 crore = 1 billion paisa


def ist_to_utc(dt_str: str) -> datetime | None:
    """Convert IST datetime string to UTC-aware datetime.

    Both BuyHatke and PriceHistory.app return IST timestamps.
    Our DB stores TIMESTAMPTZ (UTC).

    Accepted formats:
        ``"2024-10-15 00:00:33"``  (BuyHatke)
        ``"2025-09-14 11:09:40"``  (PriceHistory.app)

    Returns ``None`` if parsing fails.
    """
    if not dt_str or not dt_str.strip():
        return None
    try:
        naive = datetime.strptime(dt_str.strip(), "%Y-%m-%d %H:%M:%S")
        ist_aware = naive.replace(tzinfo=IST)
        return ist_aware.astimezone(UTC)
    except (ValueError, TypeError):
        return None


def inr_to_paisa(price_inr: float | int | str) -> Decimal:
    """Convert raw INR price to paisa (Decimal 12,2).

    BuyHatke returns prices as raw INR floats (e.g. 43499.0).
    PriceHistory.app also returns raw INR integers (e.g. 64900).
    Our system stores prices in paisa: 43499 INR → 4349900 paisa.
    """
    try:
        rupees = Decimal(str(price_inr))
        return (rupees * 100).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")


def validate_price(price_paisa: Decimal) -> bool:
    """Check if a price in paisa is within a reasonable range."""
    return _MIN_PRICE_PAISA <= price_paisa <= _MAX_PRICE_PAISA
