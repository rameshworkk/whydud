"""Rotating proxy fallback strategy for backfill HTTP clients.

Strategy:
1. Start with direct IP (no proxy)
2. On first 403 → switch to rotating proxy
3. On rotating proxy, 3 consecutive 403s → proxy burned
4. Every 30 minutes → retry direct IP to check if unblocked
5. If direct IP works → switch back to direct
6. If direct IP still blocked → continue with proxy

When no proxy URL is configured, all methods are no-ops and the
client behaves exactly as before (direct IP only).
"""
from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)


class ProxyStrategy:
    """Direct IP → rotating proxy fallback with periodic direct retry.

    Integrates with ``PHClient`` and ``BHClient`` to transparently
    switch between direct and proxied HTTP clients on 403 responses.

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
        self._proxy_burned = False
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

    @property
    def is_proxy_burned(self) -> bool:
        """True if rotating proxy exhausted its consecutive 403 threshold."""
        return self._proxy_burned

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
                should reset rate-limit counters and retry immediately
                without backoff (new IP, clean slate).
            ``"probe_failed"`` — periodic direct probe failed; caller
                should skip rate-limit bookkeeping and retry with proxy.
            ``"normal"`` — regular 403 on current mode; caller proceeds
                with standard exponential backoff.
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
            self._proxy_consecutive_403s += 1
            self._proxy_403_count += 1
            if self._proxy_consecutive_403s >= self._proxy_burn_threshold:
                self._proxy_burned = True
                logger.warning(
                    "Proxy strategy: PROXY burned — %d consecutive 403s",
                    self._proxy_consecutive_403s,
                )
            return "normal"

    # ── Stats ─────────────────────────────────────────────────────

    @property
    def stats(self) -> dict:
        return {
            "mode": self._mode,
            "proxy_enabled": self.enabled,
            "direct_403s": self._direct_403_count,
            "proxy_403s": self._proxy_403_count,
            "proxy_consecutive_403s": self._proxy_consecutive_403s,
            "proxy_burned": self._proxy_burned,
            "mode_switches": self._mode_switches,
        }
