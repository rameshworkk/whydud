"""PriceHistory.app client — async, token-based price history fetcher.

Two operating modes:

1. **Discovery (Phase 1):** Parse sitemaps + fetch HTML for ASIN/FSID extraction.
   Only fetches HTML pages — does NOT call /api/price.
2. **Deep extend (Phase 3):** Fetch HTML for token, then POST /api/price/{code}
   for full 3-5 year history + sale events.

Rate limits are stricter than BuyHatke due to Cloudflare protection.
Includes retry with exponential backoff on 403/429 and alternating
cooldown pauses (15s/30s every 3 minutes) to stay under detection.

Usage::

    async with PHClient() as client:
        # Phase 1: sitemap discovery
        sitemaps = await client.fetch_sitemap_index()
        products = await client.parse_sitemap(sitemaps[0])
        meta = await client.fetch_page_metadata("sy9uDEyp")

        # Phase 3: deep history
        meta = await client.fetch_page_metadata("sy9uDEyp")
        history = await client.fetch_price_history("sy9uDEyp", meta["token"])
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree

import httpx

from apps.pricing.backfill.config import BackfillConfig
from apps.pricing.backfill.proxy_strategy import ProxyStrategy
from apps.pricing.backfill.utils import inr_to_paisa, ist_to_utc, validate_price

logger = logging.getLogger(__name__)

# Map PH marketplace names (from JSON-LD) to our slugs
_PH_MARKETPLACE_MAP = {
    "amazon.in": "amazon-in",
    "flipkart.com": "flipkart",
    "flipkart": "flipkart",
    "croma.com": "croma",
    "myntra.com": "myntra",
    "ajio.com": "ajio",
    "tatacliq.com": "tata-cliq",
    "jiomart.com": "jiomart",
    "reliancedigital.in": "reliance-digital",
    "vijaysales.com": "vijay-sales",
    "nykaa.com": "nykaa",
    "snapdeal.com": "snapdeal",
}

# XML namespace for sitemap parsing
_SITEMAP_NS = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

# Regex patterns for HTML extraction
_TOKEN_RE = re.compile(r'"token"\s*,\s*"([a-f0-9]{40,})"')
_JSONLD_RE = re.compile(
    r'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script>',
    re.DOTALL,
)
_PH_CODE_RE = re.compile(r"-([A-Za-z0-9]{8})$")

_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
]


class AuthError(Exception):
    """PriceHistory.app returned an authentication error."""


class APIError(Exception):
    """PriceHistory.app returned an API error."""


class RateLimitError(Exception):
    """PriceHistory.app rate-limited us (403/429)."""


class PHClient:
    """Async context manager for PriceHistory.app API calls.

    Includes:
    - Retry with exponential backoff on 403/429
    - Alternating cooldown pauses (15s/30s every 3 min)
    - Adaptive delay increase on consecutive rate limits
    """

    def __init__(
        self,
        delay: float | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._html_delay = delay if delay is not None else BackfillConfig.ph_html_delay()
        self._api_delay = BackfillConfig.ph_api_delay()
        self._base_html_delay = self._html_delay
        self._base_api_delay = self._api_delay
        self._concurrency = concurrency or BackfillConfig.ph_concurrency()
        self._timeout = timeout or BackfillConfig.ph_timeout()
        self._max_retries = BackfillConfig.ph_max_retries()
        self._semaphore: asyncio.Semaphore | None = None
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        self._error_count = 0
        self._ua_idx = 0

        # Rate limit tracking
        self._consecutive_403s = 0
        self._cooldown_until: float = 0
        self._rate_limited = False

        # Alternating cooldown pause state
        self._start_time: float = 0
        self._last_cooldown_time: float = 0
        self._cooldown_cycle = 0  # alternates 0 (short) / 1 (long)
        self._cooldown_interval = BackfillConfig.ph_cooldown_interval()
        self._cooldown_short = BackfillConfig.ph_cooldown_short()
        self._cooldown_long = BackfillConfig.ph_cooldown_long()

        # Rotating proxy fallback (direct IP → proxy → periodic direct retry)
        self._proxy_strategy = ProxyStrategy(
            proxy_url=BackfillConfig.proxy_url(),
            retry_interval=BackfillConfig.proxy_retry_interval(),
            proxy_burn_threshold=BackfillConfig.proxy_burn_threshold(),
        )

    async def __aenter__(self) -> PHClient:
        self._semaphore = asyncio.Semaphore(self._concurrency)
        headers = {
            "User-Agent": _USER_AGENTS[0],
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        # Direct client (always created)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            headers=headers,
        )
        # Proxy client (only if proxy URL configured)
        self._proxy_client: httpx.AsyncClient | None = None
        if self._proxy_strategy.enabled:
            self._proxy_client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                follow_redirects=True,
                headers=headers,
                proxy=self._proxy_strategy.proxy_url,
            )
        self._start_time = time.monotonic()
        self._last_cooldown_time = self._start_time
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
        if self._proxy_client:
            await self._proxy_client.aclose()
        proxy_info = ""
        if self._proxy_strategy.enabled:
            proxy_info = f", proxy={self._proxy_strategy.stats}"
        logger.info(
            "PHClient closed: %d requests, %d errors, %d consecutive_403s%s",
            self._request_count,
            self._error_count,
            self._consecutive_403s,
            proxy_info,
        )

    def _get_client(self) -> httpx.AsyncClient:
        """Return the appropriate HTTP client based on proxy strategy mode."""
        assert self._client is not None
        if self._proxy_client and not self._proxy_strategy.use_direct:
            return self._proxy_client
        return self._client

    def _next_ua(self) -> str:
        ua = _USER_AGENTS[self._ua_idx % len(_USER_AGENTS)]
        self._ua_idx += 1
        return ua

    async def _maybe_cooldown_pause(self) -> None:
        """Check if we need an alternating cooldown pause (15s/30s every 3 min)."""
        now = time.monotonic()
        elapsed_since_last = now - self._last_cooldown_time
        if elapsed_since_last >= self._cooldown_interval:
            if self._cooldown_cycle % 2 == 0:
                pause = self._cooldown_short
            else:
                pause = self._cooldown_long
            self._cooldown_cycle += 1
            self._last_cooldown_time = now
            logger.info(
                "PH cooldown pause: %.0fs (cycle %d, elapsed %.0fs)",
                pause, self._cooldown_cycle, now - self._start_time,
            )
            await asyncio.sleep(pause)

    async def _wait_for_cooldown(self) -> None:
        """Wait if we're in a global cooldown period after exhausting retries."""
        now = time.monotonic()
        if now < self._cooldown_until:
            wait = self._cooldown_until - now
            logger.warning("PH global cooldown: waiting %.1fs", wait)
            await asyncio.sleep(wait)

    def _on_success(self) -> None:
        """Decay delay back toward base on successful request."""
        if self._consecutive_403s > 0:
            self._consecutive_403s = max(0, self._consecutive_403s - 1)
            self._html_delay = max(self._base_html_delay, self._html_delay * 0.9)
            self._api_delay = max(self._base_api_delay, self._api_delay * 0.9)
            if self._consecutive_403s == 0:
                self._rate_limited = False

    def _on_rate_limit(self) -> None:
        """Increase delay adaptively on rate limit hit."""
        self._consecutive_403s += 1
        self._error_count += 1
        self._rate_limited = True
        # Exponential backoff on delays, capped at 30s
        self._html_delay = min(self._base_html_delay * (2 ** self._consecutive_403s), 30.0)
        self._api_delay = min(self._base_api_delay * (2 ** self._consecutive_403s), 30.0)
        logger.warning(
            "PH rate limit: consecutive_403s=%d, html_delay=%.1fs, api_delay=%.1fs",
            self._consecutive_403s, self._html_delay, self._api_delay,
        )

    @property
    def is_ip_burned(self) -> bool:
        """True if consecutive 403s exceed abort threshold on direct IP."""
        return self._consecutive_403s >= BackfillConfig.ph_abort_threshold()

    @property
    def is_rate_limited(self) -> bool:
        """True if we're currently experiencing rate limiting."""
        return self._rate_limited

    @property
    def consecutive_403s(self) -> int:
        return self._consecutive_403s

    # ── Sitemap Parsing (Phase 1) ────────────────────────────────

    async def fetch_sitemap_index(self) -> list[str]:
        """Fetch the PH sitemap index → list of ``prices-N.xml`` URLs.

        Returns:
            List of full sitemap URLs, e.g.
            ``["https://pricehistory.app/sitemap/prices-1.xml", ...]``
        """
        assert self._client is not None

        url = f"{BackfillConfig.ph_base_url()}/sitemap/prices.xml"
        self._request_count += 1
        resp = await self._client.get(url, headers={"User-Agent": self._next_ua()})
        resp.raise_for_status()

        root = ElementTree.fromstring(resp.text)
        urls = []
        for loc in root.findall(".//sm:loc", _SITEMAP_NS):
            if loc.text:
                urls.append(loc.text.strip())
        logger.info("PH sitemap index: %d sub-sitemaps", len(urls))
        return urls

    async def parse_sitemap(self, sitemap_url: str) -> list[dict]:
        """Parse a single ``prices-N.xml`` → list of product dicts.

        Returns:
            List of ``{url, slug, ph_code}`` dicts.
        """
        assert self._client is not None
        assert self._semaphore is not None

        async with self._semaphore:
            await asyncio.sleep(self._html_delay)
            self._request_count += 1
            resp = await self._client.get(
                sitemap_url, headers={"User-Agent": self._next_ua()}
            )
            resp.raise_for_status()

        root = ElementTree.fromstring(resp.text)
        products = []
        for loc in root.findall(".//sm:loc", _SITEMAP_NS):
            url = loc.text.strip() if loc.text else ""
            if "/p/" not in url:
                continue
            # Extract slug and ph_code from URL
            # e.g. https://pricehistory.app/p/apple-iphone-16-pink-128-gb-sy9uDEyp
            slug = url.rsplit("/p/", 1)[-1] if "/p/" in url else ""
            match = _PH_CODE_RE.search(slug)
            if match:
                products.append({
                    "ph_url": url,
                    "slug": slug,
                    "ph_code": match.group(1),
                })

        return products

    # ── HTML Metadata Extraction (Phase 1 + Phase 3) ─────────────

    # Max free retries for proxy rotation / direct probes (safety cap)
    _MAX_FREE_RETRIES = 10

    async def fetch_page_metadata(self, ph_code: str) -> dict:
        """Fetch a PH product page and extract metadata from JSON-LD.

        Includes retry with exponential backoff on 403/429 and
        automatic proxy fallback when configured. Proxy 403s get
        free retries (rotating proxy = new IP each request).

        Args:
            ph_code: The 8-char PH product code (e.g. ``"sy9uDEyp"``).

        Returns:
            Dict with keys: ``external_id``, ``marketplace_slug``, ``title``,
            ``current_price`` (paisa), ``image_url``, ``token``, ``brand_name``.

        Raises:
            RateLimitError: If all retries exhausted on 403/429.
        """
        assert self._client is not None
        assert self._semaphore is not None

        url = f"{BackfillConfig.ph_base_url()}/p/{ph_code}"
        attempt = 0
        free_retries = 0

        while attempt < self._max_retries:
            # Check for periodic direct IP retry (30-min window)
            if self._proxy_strategy.should_retry_direct():
                self._proxy_strategy.start_direct_probe()

            # Abort immediately if IP is burned (direct mode only)
            if self.is_ip_burned:
                raise RateLimitError(
                    f"IP burned ({self._consecutive_403s} consecutive 403s) — aborting {ph_code}"
                )

            client = self._get_client()

            async with self._semaphore:
                await self._wait_for_cooldown()
                await self._maybe_cooldown_pause()
                await asyncio.sleep(self._html_delay)
                self._request_count += 1
                try:
                    resp = await client.get(
                        url, headers={"User-Agent": self._next_ua()}
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status in (403, 429):
                        action = self._proxy_strategy.on_request_403()

                        if action == "switched":
                            # Direct→Proxy: reset counters, free retry
                            self._consecutive_403s = 0
                            self._html_delay = self._base_html_delay
                            self._api_delay = self._base_api_delay
                            self._rate_limited = False
                            free_retries += 1
                            continue

                        if action in ("probe_failed", "proxy_retry", "probe_direct"):
                            # Free retry: proxy rotation or direct probe
                            free_retries += 1
                            if free_retries > self._MAX_FREE_RETRIES:
                                raise RateLimitError(
                                    f"Max proxy retries ({free_retries}) for {ph_code}"
                                ) from e
                            continue

                        # "normal" — direct mode 403 (no proxy configured)
                        self._on_rate_limit()
                        if self.is_ip_burned:
                            raise RateLimitError(
                                f"IP burned ({self._consecutive_403s} consecutive 403s) "
                                f"— aborting {ph_code}"
                            ) from e
                        attempt += 1
                        if attempt < self._max_retries:
                            wait = attempt * 15
                            logger.warning(
                                "PH HTML 403 for %s, retry %d/%d in %ds "
                                "(delay=%.1fs, mode=%s)",
                                ph_code, attempt, self._max_retries, wait,
                                self._html_delay, self._proxy_strategy.mode,
                            )
                            await asyncio.sleep(wait)
                            continue
                        # All retries exhausted — enter global cooldown
                        cooldown = min(60 * self._consecutive_403s, 300)
                        self._cooldown_until = time.monotonic() + cooldown
                        raise RateLimitError(
                            f"PH HTML rate limited after {self._max_retries} retries "
                            f"(cooldown {cooldown}s)"
                        ) from e
                    self._error_count += 1
                    return {"external_id": "", "marketplace_slug": "", "token": ""}

            # Success
            self._proxy_strategy.on_request_success()
            self._on_success()
            html = resp.text
            result = self._extract_jsonld_metadata(html)
            result["token"] = self._extract_token(html)
            return result

        # Should not reach here, but safety fallback
        return {"external_id": "", "marketplace_slug": "", "token": ""}

    @staticmethod
    def _extract_token(html: str) -> str:
        """Extract the per-page API token from HTML.

        Looks for: ``FetchHeaders.append("token", "HEX_STRING")``
        """
        match = _TOKEN_RE.search(html)
        return match.group(1) if match else ""

    @staticmethod
    def _extract_jsonld_metadata(html: str) -> dict:
        """Extract product metadata from JSON-LD ``<script>`` tags.

        Returns dict with: external_id, marketplace_slug, title,
        current_price (paisa), image_url, brand_name.
        """
        result = {
            "external_id": "",
            "marketplace_slug": "",
            "title": "",
            "current_price": Decimal("0"),
            "image_url": "",
            "brand_name": "",
        }

        for match in _JSONLD_RE.finditer(html):
            try:
                data = json.loads(match.group(1))
            except (json.JSONDecodeError, ValueError):
                continue

            # Handle @graph arrays (PH wraps everything in @graph)
            if isinstance(data, dict) and "@graph" in data:
                items = data["@graph"]
            elif isinstance(data, list):
                items = data
            else:
                items = [data]
            for item in items:
                if not isinstance(item, dict):
                    continue
                if item.get("@type") != "Product":
                    continue

                result["title"] = item.get("name", "")

                # Brand
                brand = item.get("brand", {})
                if isinstance(brand, dict):
                    result["brand_name"] = brand.get("name", "")

                # Image — can be string, list, or @id reference dict
                img = item.get("image", "")
                if isinstance(img, list) and img:
                    img = img[0]
                if isinstance(img, dict):
                    img = img.get("url", img.get("@id", ""))
                result["image_url"] = img if isinstance(img, str) else ""

                # Offers → marketplace + price
                offers = item.get("offers", {})
                if isinstance(offers, dict):
                    offered_by = offers.get("offeredBy", {})
                    if isinstance(offered_by, dict):
                        mp_name = offered_by.get("name", "").lower().strip()
                        result["marketplace_slug"] = _PH_MARKETPLACE_MAP.get(mp_name, "")
                        if mp_name and not result["marketplace_slug"]:
                            logger.warning("Unmapped marketplace: %r", mp_name)

                    raw_price = offers.get("price")
                    if raw_price is not None:
                        result["current_price"] = inr_to_paisa(raw_price)

                # Additional properties → ASIN/FSID
                props = item.get("additionalProperty", [])
                if isinstance(props, list):
                    for prop in props:
                        if isinstance(prop, dict) and prop.get("name") == "Product Code":
                            result["external_id"] = str(prop.get("value", ""))
                            break

                break  # Found the Product, done

        return result

    # ── Price History API (Phase 3) ──────────────────────────────

    async def fetch_price_history(self, ph_code: str, token: str) -> dict:
        """Fetch full price history from PH API.

        Includes retry with exponential backoff on 403/429 and
        automatic proxy fallback when configured. Proxy 403s get
        free retries (rotating proxy = new IP each request).

        Args:
            ph_code: The 8-char PH product code.
            token: Auth token from ``fetch_page_metadata(...)[\"token\"]``.

        Returns:
            Dict with: ``price_points`` (list), ``sale_events`` (list),
            ``summary`` (dict with min/max/dates).

        Raises:
            AuthError: If the token is invalid/expired.
            APIError: If the API returns a non-rate-limit error.
            RateLimitError: If all retries exhausted on 403/429.
        """
        assert self._client is not None
        assert self._semaphore is not None

        if not token:
            raise AuthError(f"No token provided for {ph_code}")

        attempt = 0
        free_retries = 0

        while attempt < self._max_retries:
            # Check for periodic direct IP retry (30-min window)
            if self._proxy_strategy.should_retry_direct():
                self._proxy_strategy.start_direct_probe()

            # Abort immediately if IP is burned
            if self.is_ip_burned:
                raise RateLimitError(
                    f"IP burned ({self._consecutive_403s} consecutive 403s) — aborting {ph_code}"
                )

            client = self._get_client()

            async with self._semaphore:
                await self._wait_for_cooldown()
                await self._maybe_cooldown_pause()
                await asyncio.sleep(self._api_delay)
                self._request_count += 1
                try:
                    resp = await client.post(
                        f"{BackfillConfig.ph_base_url()}/api/price/{ph_code}",
                        headers={
                            "User-Agent": self._next_ua(),
                            "Content-Type": "application/json",
                            "page": ph_code,
                            "token": token,
                            "Referer": f"{BackfillConfig.ph_base_url()}/p/{ph_code}",
                            "Origin": BackfillConfig.ph_base_url(),
                        },
                        json={},
                    )
                    resp.raise_for_status()
                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status in (403, 429):
                        action = self._proxy_strategy.on_request_403()

                        if action == "switched":
                            self._consecutive_403s = 0
                            self._html_delay = self._base_html_delay
                            self._api_delay = self._base_api_delay
                            self._rate_limited = False
                            free_retries += 1
                            continue

                        if action in ("probe_failed", "proxy_retry", "probe_direct"):
                            free_retries += 1
                            if free_retries > self._MAX_FREE_RETRIES:
                                raise RateLimitError(
                                    f"Max proxy retries ({free_retries}) for {ph_code}"
                                ) from e
                            continue

                        # "normal" — direct mode 403 (no proxy configured)
                        self._on_rate_limit()
                        if self.is_ip_burned:
                            raise RateLimitError(
                                f"IP burned ({self._consecutive_403s} consecutive 403s) "
                                f"— aborting {ph_code}"
                            ) from e
                        attempt += 1
                        if attempt < self._max_retries:
                            wait = attempt * 15
                            logger.warning(
                                "PH API 403 for %s, retry %d/%d in %ds "
                                "(delay=%.1fs, mode=%s)",
                                ph_code, attempt, self._max_retries, wait,
                                self._api_delay, self._proxy_strategy.mode,
                            )
                            await asyncio.sleep(wait)
                            continue
                        # All retries exhausted
                        cooldown = min(60 * self._consecutive_403s, 300)
                        self._cooldown_until = time.monotonic() + cooldown
                        raise RateLimitError(
                            f"PH API rate limited after {self._max_retries} retries "
                            f"(cooldown {cooldown}s)"
                        ) from e
                    self._error_count += 1
                    raise APIError(f"PH API error {status}") from e

            # Success
            self._proxy_strategy.on_request_success()
            self._on_success()
            body = resp.json()

            if body.get("status") is False:
                msg = body.get("message", "Unknown error")
                if "Authentication" in msg:
                    raise AuthError(msg)
                raise APIError(msg)

            return self._parse_api_response(body)

        # Should not reach here
        raise APIError(f"PH API failed for {ph_code} after {self._max_retries} retries")

    @staticmethod
    def _parse_api_response(body: dict) -> dict:
        """Parse the PH /api/price/ response into normalized data.

        Returns dict with:
            - price_points: list of {time: datetime, price: Decimal} (UTC, paisa)
            - sale_events: list of {name, start, end}
            - summary: {min_price, max_price, min_date, max_date, mrp}
        """
        from apps.pricing.backfill.bh_client import PricePoint

        price_points: list[PricePoint] = []
        history = body.get("History", {})

        # Parse main price history
        for pt in history.get("Price", []):
            if not pt.get("x") or pt.get("y") is None:
                continue
            dt = ist_to_utc(str(pt["x"]))
            if dt is None:
                continue
            price_paisa = inr_to_paisa(pt["y"])
            if validate_price(price_paisa):
                price_points.append(PricePoint(time=dt, price=price_paisa))

        # Parse sale events
        sale_events = []
        for ev in body.get("Event", []):
            sale_events.append({
                "name": ev.get("Name", ""),
                "start": ist_to_utc(ev.get("Start", "")) if ev.get("Start") else None,
                "end": ist_to_utc(ev.get("End", "")) if ev.get("End") else None,
            })

        # Summary
        price_data = body.get("Price", {})
        summary = {}
        if price_data:
            min_p = price_data.get("MinPrice")
            max_p = price_data.get("MaxPrice")
            summary = {
                "min_price": inr_to_paisa(min_p) if min_p else None,
                "max_price": inr_to_paisa(max_p) if max_p else None,
                "min_date": ist_to_utc(price_data.get("MinPriceOn", "")) if price_data.get("MinPriceOn") else None,
                "max_date": ist_to_utc(price_data.get("MaxPriceOn", "")) if price_data.get("MaxPriceOn") else None,
                "mrp": inr_to_paisa(price_data.get("MRP")) if price_data.get("MRP") else None,
            }

        return {
            "price_points": price_points,
            "point_count": len(price_points),
            "sale_events": sale_events,
            "summary": summary,
        }

    @property
    def stats(self) -> dict:
        result = {
            "requests": self._request_count,
            "errors": self._error_count,
            "consecutive_403s": self._consecutive_403s,
        }
        if self._proxy_strategy.enabled:
            result["proxy"] = self._proxy_strategy.stats
        return result
