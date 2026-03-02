"""Scrapy downloader middlewares: proxy rotation + retry with backoff.

scrapy-playwright sets the proxy at the browser context level, not per-request.
This middleware creates a named Playwright context per proxy and assigns
requests to contexts via round-robin with health tracking.

Two proxy modes (set via SCRAPING_PROXY_TYPE env var):

  "static" (default) — Each proxy URL is a distinct IP. One browser context
  per proxy, round-robin selection, ban detection with cooldowns, reserve
  rotation. Memory-safe: limits to MAX_ACTIVE_CONTEXTS (default 3).

  "rotating" — A single gateway URL (e.g. DataImpulse) assigns a different
  IP per connection. No banning (pointless — next request gets a fresh IP).
  Cycles through numbered context slots with randomized viewports to force
  Playwright to create new contexts (and thus new TCP connections = new IPs).

When no proxies are configured (SCRAPING_PROXY_LIST is empty), all requests
pass through unmodified — behaviour is identical to a no-proxy setup.
"""
import logging
import os
import random
import time
from dataclasses import dataclass
from urllib.parse import urlparse

from scrapy import signals
from scrapy.downloadermiddlewares.retry import RetryMiddleware

logger = logging.getLogger(__name__)

# Max simultaneous browser contexts (memory safety for small VPS).
MAX_ACTIVE_CONTEXTS = 3

# Byte markers for CAPTCHA detection in 200 responses.
CAPTCHA_MARKERS = (b"captcha", b"validatecaptcha", b"robot check")

# Broader markers for 503 ban detection.
BAN_BODY_MARKERS = (b"robot", b"captcha")

# Default Playwright context kwargs (same as PLAYWRIGHT_CONTEXTS["default"]).
_BASE_CONTEXT_KWARGS = {
    "locale": "en-IN",
    "timezone_id": "Asia/Kolkata",
    "viewport": {"width": 1366, "height": 768},
    "java_script_enabled": True,
    "ignore_https_errors": True,
}


# ===================================================================
# ProxyState — health tracker for a single proxy
# ===================================================================

@dataclass
class ProxyState:
    """Tracks health and ban state for a single proxy."""

    url: str
    context_name: str = ""
    is_banned: bool = False
    ban_until: float = 0.0
    consecutive_failures: int = 0
    consecutive_connection_errors: int = 0
    total_requests: int = 0
    total_failures: int = 0
    total_bans: int = 0

    def mark_success(self) -> None:
        self.consecutive_failures = 0
        self.consecutive_connection_errors = 0
        self.total_requests += 1

    def mark_ban(self, cooldown: float) -> None:
        """Apply a ban with the given cooldown (caller adds jitter)."""
        self.consecutive_failures += 1
        self.total_bans += 1
        self.total_requests += 1
        self.ban_until = time.time() + cooldown
        self.is_banned = True

    def is_available(self) -> bool:
        if not self.is_banned:
            return True
        if time.time() >= self.ban_until:
            self.is_banned = False
            logger.info("Proxy %s ban expired, available again", self.context_name)
            return True
        return False

    @property
    def remaining_ban_seconds(self) -> float:
        if not self.is_banned:
            return 0.0
        return max(0.0, self.ban_until - time.time())

    @property
    def success_rate(self) -> float:
        if self.total_requests == 0:
            return 100.0
        return (
            (self.total_requests - self.total_bans) / self.total_requests
        ) * 100


# ===================================================================
# ProxyPool — round-robin + active context limiting
# ===================================================================

class ProxyPool:
    """Round-robin proxy pool with active context limiting.

    Only ``max_active`` proxies have browser contexts at any time.
    When an active proxy is banned, its slot is given to a reserve proxy.
    """

    def __init__(
        self, proxies: list[str], max_active: int = MAX_ACTIVE_CONTEXTS
    ) -> None:
        self._all: list[ProxyState] = []
        for i, url in enumerate(proxies):
            self._all.append(
                ProxyState(url=url.strip(), context_name=f"proxy_{i}")
            )
        self._max_active = min(max_active, len(self._all))
        self._active_indices: set[int] = set(range(self._max_active))
        self._rr_index: int = 0

    @classmethod
    def from_env(cls, max_active: int = MAX_ACTIVE_CONTEXTS) -> "ProxyPool":
        raw = os.environ.get("SCRAPING_PROXY_LIST", "")
        if not raw.strip():
            return cls([], max_active)
        proxies = [p.strip() for p in raw.split(",") if p.strip()]
        logger.info("ProxyPool loaded %d proxies from env", len(proxies))
        return cls(proxies, max_active)

    @classmethod
    def from_list(
        cls, proxies: list[str], max_active: int = MAX_ACTIVE_CONTEXTS
    ) -> "ProxyPool":
        return cls(proxies, max_active)

    # --- Properties ---

    @property
    def is_empty(self) -> bool:
        return len(self._all) == 0

    @property
    def size(self) -> int:
        return len(self._all)

    @property
    def active_states(self) -> list[ProxyState]:
        return [self._all[i] for i in sorted(self._active_indices)]

    @property
    def all_states(self) -> list[ProxyState]:
        return self._all

    # --- Proxy selection ---

    def get_next_proxy(self) -> ProxyState | None:
        """Round-robin among active, available proxies. None if all banned."""
        active = self.active_states
        if not active:
            return None
        for _ in range(len(active)):
            state = active[self._rr_index % len(active)]
            self._rr_index += 1
            if state.is_available():
                return state
        return None

    def get_proxy_by_context(self, context_name: str) -> ProxyState | None:
        for state in self._all:
            if state.context_name == context_name:
                return state
        return None

    # --- Active context rotation ---

    def rotate_banned_proxy(self, banned_proxy: ProxyState) -> ProxyState | None:
        """Swap a banned active proxy for an available reserve proxy.

        Returns the newly activated proxy (needs context kwargs built) or None.
        """
        banned_idx = next(
            (i for i, s in enumerate(self._all) if s is banned_proxy), None
        )
        if banned_idx is None or banned_idx not in self._active_indices:
            return None

        for i, state in enumerate(self._all):
            if i not in self._active_indices and state.is_available():
                self._active_indices.discard(banned_idx)
                self._active_indices.add(i)
                logger.info(
                    "Rotated out banned %s, activated %s",
                    banned_proxy.context_name,
                    state.context_name,
                )
                return state
        # No reserve available — banned proxy stays in active set, will unban later
        return None

    # --- Ban status ---

    def all_proxies_banned(self) -> bool:
        """True if every proxy (active + reserve) is currently banned."""
        return all(not s.is_available() for s in self._all)

    def shortest_ban_remaining(self) -> float:
        """Seconds until the next ban expires. 0.0 if any proxy is available."""
        remaining = [
            s.remaining_ban_seconds for s in self._all if s.is_banned
        ]
        return min(remaining) if remaining else 0.0

    # --- Stats ---

    def log_stats(self) -> None:
        """Log per-proxy and overall success rates."""
        if self.is_empty:
            return
        total_reqs = 0
        total_bans = 0
        lines = ["ProxyPool stats:"]
        for state in self._all:
            total_reqs += state.total_requests
            total_bans += state.total_bans
            lines.append(
                f"  {state.context_name}: {state.total_requests} requests, "
                f"{state.total_bans} bans, {state.success_rate:.0f}% success"
            )
        overall = (
            ((total_reqs - total_bans) / total_reqs * 100)
            if total_reqs > 0
            else 100.0
        )
        lines.append(
            f"  Overall: {total_reqs} requests, {total_bans} bans, "
            f"{overall:.0f}% success"
        )
        logger.info("\n".join(lines))


# ===================================================================
# PlaywrightProxyMiddleware — Scrapy downloader middleware
# ===================================================================

class PlaywrightProxyMiddleware:
    """Assigns Playwright contexts with proxies via round-robin.

    - Limits active browser contexts to MAX_ACTIVE_CONTEXTS (memory safety).
    - Smart ban detection: 403=ban, 429=short ban, 503=conditional, 200+CAPTCHA=ban.
    - Connection errors only ban after 2 consecutive from the same proxy.
    - When all proxies are banned, pauses spider instead of falling back to
      direct requests (which would burn the server IP).
    - Logs per-proxy stats on spider close.
    """

    # Connection errors need this many consecutive hits before banning.
    CONNECTION_ERROR_THRESHOLD = 2

    def __init__(
        self,
        proxy_pool: ProxyPool,
        cooldown_base: float,
        max_cooldown: float,
        ban_threshold: int = 1,
        is_rotating: bool = False,
    ) -> None:
        self.pool = proxy_pool
        self.cooldown_base = cooldown_base
        self.max_cooldown = max_cooldown
        self.ban_threshold = ban_threshold
        self._is_rotating = is_rotating
        self._rotating_counter: int = 0
        self._proxy_context_kwargs: dict[str, dict] = {}
        self._original_download_delay: float | None = None
        self._all_banned_logged: bool = False

    @classmethod
    def from_crawler(cls, crawler):
        from common.app_settings import ScrapingConfig

        max_active = crawler.settings.getint(
            "PROXY_MAX_ACTIVE_CONTEXTS", MAX_ACTIVE_CONTEXTS
        )

        # CLI --proxy-list override takes priority
        proxy_list_override = crawler.settings.get("PROXY_LIST_OVERRIDE")
        if proxy_list_override:
            proxies = [
                p.strip() for p in proxy_list_override.split(",") if p.strip()
            ]
            pool = ProxyPool.from_list(proxies, max_active)
        else:
            pool = ProxyPool.from_env(max_active)

        cooldown_base = ScrapingConfig.proxy_ban_cooldown_base()
        max_cooldown = ScrapingConfig.proxy_ban_max_cooldown()
        ban_threshold = ScrapingConfig.proxy_ban_threshold()

        # Check if this is a rotating proxy (single gateway, different IP each time)
        # User sets SCRAPING_PROXY_TYPE=rotating in .env (default: "static")
        proxy_type = os.environ.get("SCRAPING_PROXY_TYPE", "static").strip().lower()
        is_rotating = proxy_type == "rotating"

        middleware = cls(
            pool, cooldown_base, max_cooldown, ban_threshold, is_rotating
        )

        if pool.is_empty:
            logger.info(
                "PlaywrightProxyMiddleware: no proxies configured, "
                "falling back to direct requests"
            )
        elif is_rotating:
            logger.info(
                "PlaywrightProxyMiddleware: ROTATING mode — "
                "no banning, fresh context per request batch "
                "(%d proxy gateway(s))",
                pool.size,
            )
        else:
            logger.info(
                "PlaywrightProxyMiddleware: %d proxies loaded, "
                "%d active contexts (max %d)",
                pool.size,
                len(pool.active_states),
                max_active,
            )
            # Pre-build context kwargs only for initially active proxies
            for state in pool.active_states:
                middleware._build_context_kwargs(state)

        # Log stats when spider closes
        crawler.signals.connect(
            middleware._spider_closed, signal=signals.spider_closed
        )

        return middleware

    def _build_context_kwargs(self, state: ProxyState) -> dict:
        """Build and cache Playwright context kwargs for a proxy."""
        ctx_kwargs = {**_BASE_CONTEXT_KWARGS}
        ctx_kwargs["proxy"] = _parse_proxy_url(state.url)
        self._proxy_context_kwargs[state.context_name] = ctx_kwargs
        return ctx_kwargs

    def _compute_cooldown(
        self,
        consecutive: int,
        cooldown_override: float | None = None,
    ) -> float:
        """Compute cooldown with exponential backoff and jitter."""
        if cooldown_override is not None:
            base = cooldown_override
        else:
            base = min(
                self.cooldown_base
                * (2 ** max(0, consecutive - self.ban_threshold)),
                self.max_cooldown,
            )
        return base * (1 + random.uniform(-0.2, 0.2))

    # ------------------------------------------------------------------
    # Ban detection
    # ------------------------------------------------------------------

    def _detect_ban(self, response) -> tuple[bool, str, float | None]:
        """Analyze response for ban signals.

        Returns ``(is_ban, reason, cooldown_override_or_None)``.
        ``cooldown_override`` lets 429s use shorter cooldowns.
        """
        status = response.status

        # 403 = definite ban
        if status == 403:
            return True, "HTTP 403 Forbidden", None

        # 429 = rate limit, shorter cooldown
        if status == 429:
            return True, "HTTP 429 Rate Limited", 30.0

        # 503 = only a ban if body has markers or is tiny (<1KB)
        if status == 503:
            body = response.body
            body_lower = body[:5000].lower()
            if len(body) < 1024 or any(
                m in body_lower for m in BAN_BODY_MARKERS
            ):
                return True, "HTTP 503 with ban markers", None
            return False, "", None

        # 200 + CAPTCHA markers in body = definite ban
        if status == 200:
            body_prefix = response.body[:5000].lower()
            if any(m in body_prefix for m in CAPTCHA_MARKERS):
                return True, "CAPTCHA detected in 200 response", None

        return False, "", None

    # ------------------------------------------------------------------
    # process_request — assign proxy context
    # ------------------------------------------------------------------

    def process_request(self, request, spider):
        if not request.meta.get("playwright"):
            return None
        if self.pool.is_empty:
            return None

        if self._is_rotating:
            return self._process_rotating(request)
        else:
            return self._process_static(request, spider)

    def _process_rotating(self, request):
        """For rotating proxies: use numbered contexts that cycle.

        Creates contexts like "rotating_0", "rotating_1", ..., "rotating_4".
        Each context gets ~5 requests, then we move to the next one.
        After all 5 are used, we cycle back, but Playwright will have
        closed idle ones, forcing a new connection = new IP.
        """
        # Use a pool of 5 context slots, cycling through them
        # This gives Playwright time to close idle contexts
        ctx_index = self._rotating_counter % 5
        context_name = f"rotating_{ctx_index}"
        self._rotating_counter += 1

        proxy_state = self.pool.all_states[0]  # Only one gateway for rotating
        proxy_dict = _parse_proxy_url(proxy_state.url)

        request.meta["playwright_context"] = context_name
        request.meta["_proxy_context_name"] = context_name
        request.meta["playwright_context_kwargs"] = {
            **_BASE_CONTEXT_KWARGS,
            "proxy": proxy_dict,
        }

        # Force new context every N requests by randomizing viewport
        # (different viewport = Playwright creates new context)
        request.meta["playwright_context_kwargs"]["viewport"] = {
            "width": random.choice([1280, 1366, 1440, 1536, 1920]),
            "height": random.choice([720, 768, 864, 900, 1080]),
        }

        return None

    def _process_static(self, request, spider):
        """For static proxies: round-robin with health tracking and banning."""
        proxy = self.pool.get_next_proxy()

        if proxy is not None:
            # Restore download_delay if it was inflated by all-banned pause
            if self._original_download_delay is not None:
                spider.download_delay = self._original_download_delay
                self._original_download_delay = None

            # Reset log-once flag — a proxy recovered
            self._all_banned_logged = False

            request.meta["playwright_context"] = proxy.context_name
            request.meta["_proxy_context_name"] = proxy.context_name
            if proxy.context_name in self._proxy_context_kwargs:
                request.meta["playwright_context_kwargs"] = (
                    self._proxy_context_kwargs[proxy.context_name]
                )
            return None

        # All active proxies banned — check reserves too
        if self.pool.all_proxies_banned():
            if not self._all_banned_logged:
                shortest_ban = min(
                    (s.ban_until for s in self.pool.all_states if s.is_banned),
                    default=time.time(),
                )
                remaining = max(shortest_ban - time.time(), 0)
                logger.warning(
                    "All %d proxies banned. Next recovery in %.0fs. "
                    "Requests will use default (no proxy) context until then.",
                    self.pool.size,
                    remaining,
                )
                self._all_banned_logged = True
            # Inflate download_delay to pause the spider
            wait_time = self.pool.shortest_ban_remaining()
            if self._original_download_delay is None:
                self._original_download_delay = getattr(
                    spider, "download_delay", 0
                )
            spider.download_delay = wait_time
            # Reschedule — don't fall back to direct (burns server IP)
            return request.replace(dont_filter=True)

        # Some reserve proxies available but not active — shouldn't normally
        # happen since rotate_banned_proxy swaps them in, but handle it.
        logger.warning(
            "No active proxy available for %s, rescheduling",
            request.url[:80],
        )
        return request.replace(dont_filter=True)

    # ------------------------------------------------------------------
    # process_response — detect bans and update health
    # ------------------------------------------------------------------

    def process_response(self, request, response, spider):
        context_name = request.meta.get("_proxy_context_name")
        if not context_name:
            return response

        if self._is_rotating:
            return self._process_rotating_response(request, response, context_name)
        else:
            return self._process_static_response(request, response, context_name)

    def _process_rotating_response(self, request, response, context_name):
        """For rotating proxies: track stats but NEVER ban.

        With rotating proxies, each request gets a different IP.
        Banning the gateway URL is pointless — the next request
        will have a fresh IP automatically.
        """
        proxy = self.pool.all_states[0]  # Only one gateway

        is_captcha = False
        if response.status in (403, 429):
            is_captcha = True
        elif response.status == 200:
            body_prefix = response.body[:5000].lower()
            if any(marker in body_prefix for marker in CAPTCHA_MARKERS):
                is_captcha = True

        if is_captcha:
            proxy.total_failures += 1
            proxy.total_requests += 1
            # DON'T ban — just log
            logger.info(
                "Rotating proxy CAPTCHA on %s (total: %d/%d failures)",
                request.url[:60],
                proxy.total_failures,
                proxy.total_requests,
            )
            # Set flag so spider knows to skip (not retry)
            response.meta["_is_captcha"] = True
        else:
            proxy.total_requests += 1

        return response

    def _process_static_response(self, request, response, context_name):
        """For static proxies: detect bans, track health, rotate reserves."""
        proxy = self.pool.get_proxy_by_context(context_name)
        if not proxy:
            return response

        is_ban, reason, cooldown_override = self._detect_ban(response)

        if is_ban:
            proxy.consecutive_failures += 1
            proxy.consecutive_connection_errors = 0

            if proxy.consecutive_failures >= self.ban_threshold:
                cooldown = self._compute_cooldown(
                    proxy.consecutive_failures, cooldown_override
                )
                proxy.mark_ban(cooldown)
                logger.warning(
                    "Proxy %s banned for %.0fs — %s (failures: %d)",
                    context_name,
                    cooldown,
                    reason,
                    proxy.consecutive_failures,
                )
                # Try to swap in a reserve proxy
                new_proxy = self.pool.rotate_banned_proxy(proxy)
                if new_proxy:
                    self._build_context_kwargs(new_proxy)
            else:
                proxy.total_requests += 1
                logger.info(
                    "%s on %s via %s (%d/%d before ban)",
                    reason,
                    request.url[:80],
                    context_name,
                    proxy.consecutive_failures,
                    self.ban_threshold,
                )
        else:
            proxy.mark_success()

        return response

    # ------------------------------------------------------------------
    # process_exception — connection errors (ban after 2 consecutive)
    # ------------------------------------------------------------------

    def process_exception(self, request, exception, spider):
        context_name = request.meta.get("_proxy_context_name")
        if not context_name:
            return None

        if self._is_rotating:
            # Just track, don't ban
            proxy = self.pool.all_states[0]
            proxy.total_failures += 1
            proxy.total_requests += 1
            logger.info(
                "Rotating proxy exception: %s on %s",
                type(exception).__name__,
                request.url[:60],
            )
            return None

        # Static proxy: ban after consecutive connection errors
        proxy = self.pool.get_proxy_by_context(context_name)
        if not proxy:
            return None

        proxy.consecutive_connection_errors += 1
        proxy.total_requests += 1

        if proxy.consecutive_connection_errors >= self.CONNECTION_ERROR_THRESHOLD:
            cooldown = self._compute_cooldown(
                proxy.consecutive_connection_errors
            )
            proxy.mark_ban(cooldown)
            logger.warning(
                "Proxy %s banned for %.0fs after %d consecutive "
                "connection errors: %s",
                context_name,
                cooldown,
                proxy.consecutive_connection_errors,
                type(exception).__name__,
            )
            new_proxy = self.pool.rotate_banned_proxy(proxy)
            if new_proxy:
                self._build_context_kwargs(new_proxy)
        else:
            logger.info(
                "Connection error on %s via %s (%d/%d before ban): %s",
                request.url[:80],
                context_name,
                proxy.consecutive_connection_errors,
                self.CONNECTION_ERROR_THRESHOLD,
                type(exception).__name__,
            )

        return None

    # ------------------------------------------------------------------
    # spider_closed signal — log stats
    # ------------------------------------------------------------------

    def _spider_closed(self, spider, reason):
        if self._is_rotating:
            self._log_rotating_stats()
        else:
            self.pool.log_stats()

    def _log_rotating_stats(self) -> None:
        """Log stats for rotating proxy mode (failure-based, not ban-based)."""
        if self.pool.is_empty:
            return
        for state in self.pool.all_states:
            if state.total_requests > 0:
                success_rate = (
                    (state.total_requests - state.total_failures)
                    / state.total_requests
                ) * 100
                logger.info(
                    "Proxy stats — %s: %d requests, %d failures "
                    "(%.0f%% success)",
                    state.context_name,
                    state.total_requests,
                    state.total_failures,
                    success_rate,
                )


# ===================================================================
# Helpers
# ===================================================================

def _parse_proxy_url(proxy_url: str) -> dict:
    """Convert a proxy URL to Playwright's proxy dict format.

    ``http://user:pass@host:port`` → ``{"server": "http://host:port", ...}``
    ``http://host:port``           → ``{"server": "http://host:port"}``
    ``socks5://host:port``         → ``{"server": "socks5://host:port"}``
    """
    parsed = urlparse(proxy_url)
    result: dict[str, str] = {
        "server": f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
    }
    if parsed.username:
        result["username"] = parsed.username
    if parsed.password:
        result["password"] = parsed.password
    return result


# ===================================================================
# BackoffRetryMiddleware — exponential backoff on retries
# ===================================================================

class BackoffRetryMiddleware(RetryMiddleware):
    """Retry middleware with non-blocking exponential backoff.

    Overrides process_response / process_exception (public API) rather
    than the internal _retry — avoids signature mismatches across Scrapy
    versions.  Adds ``download_delay`` to the retried request so
    Scrapy's scheduler handles the pause asynchronously.
    """

    BACKOFF_BASE = 5        # first retry gets 5s extra delay
    BACKOFF_MAX = 60        # cap at 60s
    BACKOFF_JITTER = 0.3    # ±30% randomization

    def _add_backoff(self, result, request, spider):
        """If *result* is a retry Request, attach a backoff delay to it."""
        from scrapy.http import Request as ScrapyRequest

        if not isinstance(result, ScrapyRequest):
            return result
        retries = result.meta.get("retry_times", 0)
        delay = min(self.BACKOFF_BASE * (2 ** retries), self.BACKOFF_MAX)
        delay *= 1 + random.uniform(-self.BACKOFF_JITTER, self.BACKOFF_JITTER)
        result.meta["download_delay"] = delay
        spider.logger.info(
            f"Backoff retry #{retries}: {delay:.1f}s delay for {request.url[:80]}"
        )
        return result

    def process_response(self, request, response, spider):
        result = super().process_response(request, response, spider)
        return self._add_backoff(result, request, spider)

    def process_exception(self, request, exception, spider):
        result = super().process_exception(request, exception, spider)
        return self._add_backoff(result, request, spider)
