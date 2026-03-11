"""Rotating proxy fallback strategy for backfill HTTP clients.

Strategy:
1. Start with direct IP (no proxy)
2. On first 403 → switch to rotating proxy
3. On proxy 403 → retry immediately (rotating = new IP each request)
4. After N consecutive proxy 403s → probe direct IP to check if recovered
5. Every 30 minutes → also probe direct IP
6. If direct IP works → switch back to direct
7. If direct IP still blocked → continue with proxy

Rotating proxy never "burns" — each request goes through a different IP.
When no proxy URL is configured, all methods are no-ops.
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class ProxyStrategy:
    """Direct IP → rotating proxy fallback with periodic direct retry.

    Integrates with ``PHClient`` and ``BHClient`` to transparently
    switch between direct and proxied HTTP clients on 403 responses.

    Rotating proxy gets a new IP per request, so 403 on proxy just
    means "try again" — never abort or cooldown on proxy 403.

    When ``proxy_url`` is empty, :attr:`enabled` is ``False`` and all
    methods are effectively no-ops — existing behavior is preserved.
    """

    MODE_DIRECT = "direct"
    MODE_PROXY = "proxy"

    def __init__(
        self,
        proxy_url: str | None = None,
        retry_interval: float = 1800.0,
        proxy_burn_threshold: int = 3,
    ) -> None:
        self._proxy_url = proxy_url or ""
        self._retry_interval = retry_interval
        self._proxy_burn_threshold = proxy_burn_threshold

        self._mode = self.MODE_DIRECT
        self._proxy_consecutive_403s = 0
        self._probing_direct = False
        self._last_direct_retry_time: float = time.monotonic()

        # Stats
        self._direct_403_count = 0
        self._proxy_403_count = 0
        self._mode_switches = 0

    # ── Properties ────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        """True if a rotating proxy URL is configured."""
        return bool(self._proxy_url)

    @property
    def mode(self) -> str:
        return self._mode

    @property
    def use_direct(self) -> bool:
        """True if current request should use direct IP."""
        return self._mode == self.MODE_DIRECT or self._probing_direct

    @property
    def proxy_url(self) -> str:
        return self._proxy_url

    # ── Periodic direct retry ─────────────────────────────────────

    def should_retry_direct(self) -> bool:
        """True if 30-min window elapsed and we should probe direct IP."""
        if not self.enabled or self._mode != self.MODE_PROXY:
            return False
        return (time.monotonic() - self._last_direct_retry_time) >= self._retry_interval

    def start_direct_probe(self) -> None:
        """Begin a direct IP probe attempt.

        Sets ``use_direct=True`` for the next request so the caller
        uses the direct client. Call :meth:`on_request_success` or
        :meth:`on_request_403` after the request to finalize the probe.
        """
        self._probing_direct = True
        self._last_direct_retry_time = time.monotonic()
        logger.info("Proxy strategy: probing direct IP (30-min periodic retry)")

    # ── Request outcome callbacks ─────────────────────────────────

    def on_request_success(self) -> None:
        """Call on any successful (non-403) response."""
        if self._probing_direct:
            self._probing_direct = False
            self._mode = self.MODE_DIRECT
            self._mode_switches += 1
            logger.info(
                "Proxy strategy: direct IP recovered — switching back to DIRECT"
            )
            return
        if self._mode == self.MODE_PROXY:
            self._proxy_consecutive_403s = 0

    def on_request_403(self) -> str:
        """Call on 403/429 response.

        Returns:
            ``"switched"`` — just switched from direct to proxy; caller
                should reset rate-limit counters and retry immediately.
            ``"probe_failed"`` — periodic direct probe failed; caller
                should retry with proxy (free retry, no backoff).
            ``"proxy_retry"`` — proxy got 403 but rotating proxy gives
                new IP each request; caller should retry immediately
                (free retry, no backoff, no rate-limit bookkeeping).
            ``"probe_direct"`` — after N consecutive proxy 403s, probing
                direct IP; caller should retry with direct client
                (free retry, no backoff).
            ``"normal"`` — regular 403 on direct mode (no proxy configured);
                caller proceeds with standard exponential backoff.
        """
        if self._probing_direct:
            self._probing_direct = False
            self._direct_403_count += 1
            logger.info(
                "Proxy strategy: direct probe still blocked — staying on PROXY"
            )
            return "probe_failed"

        if self._mode == self.MODE_DIRECT:
            self._direct_403_count += 1
            if self.enabled:
                self._mode = self.MODE_PROXY
                self._proxy_consecutive_403s = 0
                self._mode_switches += 1
                logger.info(
                    "Proxy strategy: 403 on direct IP — switching to PROXY "
                    "(total direct 403s: %d)",
                    self._direct_403_count,
                )
                return "switched"
            return "normal"
        else:
            # Rotating proxy — each request is a new IP, never abort
            self._proxy_consecutive_403s += 1
            self._proxy_403_count += 1
            if self._proxy_consecutive_403s >= self._proxy_burn_threshold:
                # After N consecutive proxy 403s, probe direct IP
                # (maybe it recovered while we were on proxy)
                self._proxy_consecutive_403s = 0
                self._probing_direct = True
                self._last_direct_retry_time = time.monotonic()
                logger.info(
                    "Proxy strategy: %d consecutive proxy 403s — probing "
                    "direct IP (proxy 403s: %d)",
                    self._proxy_burn_threshold,
                    self._proxy_403_count,
                )
                return "probe_direct"
            return "proxy_retry"

    # ── Stats ─────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "mode": self._mode,
            "proxy_enabled": self.enabled,
            "direct_403s": self._direct_403_count,
            "proxy_403s": self._proxy_403_count,
            "proxy_consecutive_403s": self._proxy_consecutive_403s,
            "mode_switches": self._mode_switches,
        }
