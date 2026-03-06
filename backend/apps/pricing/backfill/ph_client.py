"""PriceHistory.app client — async, token-based price history fetcher.

Two operating modes:

1. **Discovery (Phase 1):** Parse sitemaps + fetch HTML for ASIN/FSID extraction.
   Only fetches HTML pages — does NOT call /api/price.
2. **Deep extend (Phase 3):** Fetch HTML for token, then POST /api/price/{code}
   for full 3-5 year history + sale events.

Rate limits are stricter than BuyHatke due to Cloudflare protection.

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
from datetime import datetime
from decimal import Decimal
from xml.etree import ElementTree

import httpx

from apps.pricing.backfill.config import BackfillConfig
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


class PHClient:
    """Async context manager for PriceHistory.app API calls."""

    def __init__(
        self,
        delay: float | None = None,
        concurrency: int | None = None,
        timeout: float | None = None,
    ) -> None:
        self._html_delay = delay if delay is not None else BackfillConfig.ph_html_delay()
        self._api_delay = BackfillConfig.ph_api_delay()
        self._concurrency = concurrency or BackfillConfig.ph_concurrency()
        self._timeout = timeout or BackfillConfig.ph_timeout()
        self._semaphore: asyncio.Semaphore | None = None
        self._client: httpx.AsyncClient | None = None
        self._request_count = 0
        self._error_count = 0
        self._ua_idx = 0

    async def __aenter__(self) -> PHClient:
        self._semaphore = asyncio.Semaphore(self._concurrency)
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(self._timeout),
            follow_redirects=True,
            headers={
                "User-Agent": _USER_AGENTS[0],
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._client:
            await self._client.aclose()
        logger.info(
            "PHClient closed: %d requests, %d errors",
            self._request_count,
            self._error_count,
        )

    def _next_ua(self) -> str:
        ua = _USER_AGENTS[self._ua_idx % len(_USER_AGENTS)]
        self._ua_idx += 1
        return ua

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

    async def fetch_page_metadata(self, ph_code: str) -> dict:
        """Fetch a PH product page and extract metadata from JSON-LD.

        Args:
            ph_code: The 8-char PH product code (e.g. ``"sy9uDEyp"``).

        Returns:
            Dict with keys: ``external_id``, ``marketplace_slug``, ``title``,
            ``current_price`` (paisa), ``image_url``, ``token``, ``brand_name``.
        """
        assert self._client is not None
        assert self._semaphore is not None

        # We need the full slug URL, but we can construct a minimal one
        # PH redirects /p/CODE to the full slug URL
        url = f"{BackfillConfig.ph_base_url()}/p/{ph_code}"

        async with self._semaphore:
            await asyncio.sleep(self._html_delay)
            self._request_count += 1
            try:
                resp = await self._client.get(
                    url, headers={"User-Agent": self._next_ua()}
                )
                resp.raise_for_status()
            except httpx.HTTPStatusError:
                self._error_count += 1
                return {"external_id": "", "marketplace_slug": "", "token": ""}

        html = resp.text
        result = self._extract_jsonld_metadata(html)
        result["token"] = self._extract_token(html)
        return result

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

        Requires a fresh token extracted from the HTML page.

        Args:
            ph_code: The 8-char PH product code.
            token: Auth token from ``fetch_page_metadata(...)[\"token\"]``.

        Returns:
            Dict with: ``price_points`` (list), ``sale_events`` (list),
            ``summary`` (dict with min/max/dates).

        Raises:
            AuthError: If the token is invalid/expired.
            APIError: If the API returns an error.
        """
        assert self._client is not None
        assert self._semaphore is not None

        if not token:
            raise AuthError(f"No token provided for {ph_code}")

        async with self._semaphore:
            await asyncio.sleep(self._api_delay)
            self._request_count += 1
            try:
                resp = await self._client.post(
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
                self._error_count += 1
                raise APIError(f"PH API error {e.response.status_code}") from e

        body = resp.json()

        if body.get("status") is False:
            msg = body.get("message", "Unknown error")
            if "Authentication" in msg:
                raise AuthError(msg)
            raise APIError(msg)

        return self._parse_api_response(body)

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
    def stats(self) -> dict[str, int]:
        return {"requests": self._request_count, "errors": self._error_count}
