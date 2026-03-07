"""BuyHatke API client — async, zero-auth price history fetcher.

Uses ``httpx`` (already in requirements) for async HTTP.
All endpoints are open (no auth tokens needed).
Rate-limited via ``asyncio.Semaphore`` + per-request delay.

Endpoints used:
    - ``graph.bitbns.com/getPredictedData.php`` — price history (tilde-delimited)
    - ``graph.bitbns.com/getPopular.php`` — popularity data (JSON array)
    - ``search-new.bitbns.com/buyhatke/comparePrice`` — cross-marketplace prices

Usage::

    async with BHClient() as client:
        result = await client.fetch_price_history("B09G9HD6PD", "amazon-in")
        print(result.point_count, result.prediction)
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

import httpx

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.utils import inr_to_paisa, ist_to_utc, validate_price

logger = logging.getLogger(__name__)

# Rotating User-Agents for politeness
_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:123.0) Gecko/20100101 Firefox/123.0",
]


@dataclass
class PricePoint:
    """A single price observation — already in paisa + UTC."""

    time: datetime
    price: Decimal  # paisa


@dataclass
class PriceHistoryResult:
    """Result from ``fetch_price_history``."""

    found: bool
    price_points: list[PricePoint] = field(default_factory=list)
    point_count: int = 0
    prediction: dict[str, int] = field(default_factory=dict)


@dataclass
class PopularityResult:
    """Result from ``fetch_popularity``."""

    found: bool
    data_points: list[dict] = field(default_factory=list)


@dataclass
class CompareResult:
    """Result from ``fetch_compare_prices``."""

    found: bool
    prices: list[dict] = field(default_factory=list)


class BHClient:
    """Async context manager for BuyHatke API calls.

    Controls concurrency via ``asyncio.Semaphore`` and adds
    a delay between requests for politeness.
    """

    def __init__(
        self,
        delay: float | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._delay = delay if delay is not None else BackfillConfig.bh_delay()
        self._concurrency = concurrency or BackfillConfig.bh_concurrency()
        self._timeout = timeout or BackfillConfig.bh_timeout()
        self._semaphore: asyncio.Semaphore | None = None
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        self._error_count = 0
        self._ua_idx = 0

    async def __aenter__(self) -> BHClient:
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            headers={"User-Agent": _USER_AGENTS[0]},
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
        logger.info(
            "BHClient closed: %d requests, %d errors",
            self._request_count,
            self._error_count,
        )

    def _next_ua(self) -> str:
        """Round-robin User-Agent rotation."""
        ua = _USER_AGENTS[self._ua_idx % len(_USER_AGENTS)]
        self._ua_idx += 1
        return ua

    # ── Price History ────────────────────────────────────────────

    async def fetch_price_history(
        self, pid: str, marketplace_slug: str
    ) -> PriceHistoryResult:
        """Fetch price history for a product from BuyHatke.

        Args:
            pid: Product identifier (ASIN for Amazon, FSID for Flipkart).
            marketplace_slug: Our marketplace slug (e.g. ``"amazon-in"``).

        Returns:
            ``PriceHistoryResult`` with parsed price points in paisa + UTC.
        """
        pos_map = BackfillConfig.bh_pos_map()
        pos = pos_map.get(marketplace_slug)
        if pos is None:
            return PriceHistoryResult(found=False)

        params: dict[str, str] = {
            "type": "log",
            "indexName": "interest_centers",
            "logName": "info",
            "pos": str(pos),
            "pid": pid,
        }
        if pos == 63:  # Amazon requires mainFL=1
            params["mainFL"] = "1"

        assert self._semaphore is not None
        assert self._client is not None

        async with self._semaphore:
            await asyncio.sleep(self._delay)
            self._request_count += 1

            max_retries = BackfillConfig.bh_max_retries()
            for attempt in range(max_retries):
                try:
                    resp = await self._client.get(
                        f"{BackfillConfig.bh_base_url()}/getPredictedData.php",
                        params=params,
                        headers={"User-Agent": self._next_ua()},
                    )
                    resp.raise_for_status()
                    return self._parse_price_history(resp.text)

                except httpx.HTTPStatusError as e:
                    if e.response.status_code in (429, 403) and attempt < max_retries - 1:
                        wait = (attempt + 1) * 10
                        logger.warning(
                            "BH rate limited (%d), waiting %ds (attempt %d/%d)",
                            e.response.status_code, wait, attempt + 1, max_retries,
                        )
                        await asyncio.sleep(wait)
                        continue
                    if e.response.status_code in (429, 403):
                        # All retries exhausted — pause longer before next product
                        logger.warning("BH blocked, pausing 60s before continuing")
                        await asyncio.sleep(60)
                    self._error_count += 1
                    raise

                except (httpx.TimeoutException, httpx.ConnectError):
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 * (attempt + 1))
                        continue
                    self._error_count += 1
                    raise

        return PriceHistoryResult(found=False)  # unreachable, satisfies type checker

    @staticmethod
    def _parse_price_history(text: str) -> PriceHistoryResult:
        """Parse BuyHatke tilde-delimited response.

        Format::

            2024-10-15 00:00:33~43499~*~*2024-10-16 00:00:38~42999~*~*...&~&~100&~&~50&~&~47

        Entries separated by ``~*~*``, last entry has predictions after ``&~&~``.
        """
        if not text or not text.strip():
            return PriceHistoryResult(found=False)

        text = text.strip()
        prediction: dict[str, int] = {"days": 100, "weeks": 100, "months": 100}
        price_points: list[PricePoint] = []

        entries = text.split("~*~*")

        for entry in entries:
            entry = entry.strip()
            if not entry:
                continue

            if "&~&~" in entry:
                # Last entry contains prediction percentages
                parts = entry.split("&~&~")
                try:
                    if len(parts) >= 4:
                        prediction = {
                            "days": int(parts[1]),
                            "weeks": int(parts[2]),
                            "months": int(parts[3]),
                        }
                    elif len(parts) == 3:
                        prediction = {
                            "days": int(parts[0]) if parts[0] else 100,
                            "weeks": int(parts[1]),
                            "months": int(parts[2]),
                        }
                except (ValueError, IndexError):
                    pass
                # There may be a price point before the &~&~ separator
                pre = parts[0].strip()
                if pre and "~" in pre:
                    pt = BHClient._parse_single_point(pre)
                    if pt:
                        price_points.append(pt)
            else:
                pt = BHClient._parse_single_point(entry)
                if pt:
                    price_points.append(pt)

        found = len(price_points) > 0
        return PriceHistoryResult(
            found=found,
            price_points=price_points,
            point_count=len(price_points),
            prediction=prediction,
        )

    @staticmethod
    def _parse_single_point(entry: str) -> PricePoint | None:
        """Parse a single ``date~price`` entry."""
        parts = entry.split("~")
        if len(parts) < 2:
            return None
        try:
            dt = ist_to_utc(parts[0])
            if dt is None:
                return None
            raw_price = float(parts[1])
            price_paisa = inr_to_paisa(raw_price)
            if not validate_price(price_paisa):
                return None
            return PricePoint(time=dt, price=price_paisa)
        except (ValueError, IndexError):
            return None

    # ── Popularity ───────────────────────────────────────────────

    async def fetch_popularity(
        self, pid: str, marketplace_slug: str
    ) -> PopularityResult:
        """Fetch popularity time series for a product."""
        pos_map = BackfillConfig.bh_pos_map()
        pos = pos_map.get(marketplace_slug)
        if pos is None:
            return PopularityResult(found=False)

        assert self._semaphore is not None
        assert self._client is not None

        async with self._semaphore:
            await asyncio.sleep(self._delay)
            self._request_count += 1
            try:
                resp = await self._client.get(
                    f"{BackfillConfig.bh_base_url()}/getPopular.php",
                    params={"pos": str(pos), "pid": pid},
                    headers={"User-Agent": self._next_ua()},
                )
                resp.raise_for_status()
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    return PopularityResult(found=True, data_points=data)
                return PopularityResult(found=False)
            except Exception:
                self._error_count += 1
                return PopularityResult(found=False)

    # ── Cross-Marketplace Comparison ─────────────────────────────

    async def fetch_compare_prices(
        self, pid: str, marketplace_slug: str
    ) -> CompareResult:
        """Fetch cross-marketplace price comparison."""
        pos_map = BackfillConfig.bh_pos_map()
        pos = pos_map.get(marketplace_slug)
        if pos is None:
            return CompareResult(found=False)

        assert self._semaphore is not None
        assert self._client is not None

        async with self._semaphore:
            await asyncio.sleep(self._delay)
            self._request_count += 1
            try:
                resp = await self._client.get(
                    f"{BackfillConfig.bh_compare_url()}/buyhatke/comparePrice",
                    params={"PID": pid, "pos": str(pos)},
                    headers={"User-Agent": self._next_ua()},
                )
                resp.raise_for_status()
                body = resp.json()
                if body.get("status") == 1 and body.get("data"):
                    return CompareResult(found=True, prices=body["data"])
                return CompareResult(found=False)
            except Exception:
                self._error_count += 1
                return CompareResult(found=False)

    @property
    def stats(self) -> dict[str, int]:
        """Request/error counters."""
        return {"requests": self._request_count, "errors": self._error_count}
