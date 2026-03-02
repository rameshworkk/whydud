"""Scrapy downloader middlewares: proxy rotation + retry with backoff.

Supports TWO proxy modes controlled by SCRAPING_PROXY_TYPE env var:

  SCRAPING_PROXY_TYPE=rotating  (DataImpulse, SmartProxy, etc.)
    - ONE gateway URL that gives a different IP per connection
    - NEVER bans the gateway — each request gets a fresh IP
    - Uses a single Playwright context (reuses the connection)
    - CAPTCHA/403 = normal (~20-30%), just track stats, don't ban
    - Spider should retry once then skip

  SCRAPING_PROXY_TYPE=static  (WebShare, individual proxies)
    - Multiple fixed-IP proxies, round-robin with health tracking
    - Bans individual proxies on failures with exponential backoff
    - Original behavior preserved

When no proxies are configured (SCRAPING_PROXY_LIST is empty), all requests
pass through unmodified — behaviour is identical to a no-proxy setup.
"""
import logging
import os
import random
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import scrapy
from scrapy.downloadermiddlewares.retry import RetryMiddleware

logger = logging.getLogger(__name__)

# HTTP status codes that indicate a proxy ban / rate-limit.
BAN_STATUS_CODES = {403, 429}

# Byte-level markers checked in the first 5 KB of a response body.
CAPTCHA_MARKERS = (b"captcha", b"validatecaptcha", b"robot check")

# Default Playwright context kwargs.
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
    total_requests: int = 0
    total_failures: int = 0

    def mark_success(self) -> None:
        self.consecutive_failures = 0
        self.is_banned = False
        self.ban_until = 0.0
        self.total_requests += 1

    def mark_failure(
        self, cooldown_base: float = 60.0, max_cooldown: float = 900.0
    ) -> None:
        self.consecutive_failures += 1
        self.total_failures += 1
        self.total_requests += 1
        cooldown = min(
            cooldown_base * (2 ** (self.consecutive_failures - 1)), max_cooldown
        )
        cooldown *= 1 + random.uniform(-0.2, 0.2)
        self.ban_until = time.time() + cooldown
        self.is_banned = True
        logger.warning(
            "Proxy %s banned for %.0fs (consecutive failures: %d)",
            self.context_name,
            cooldown,
            self.consecutive_failures,
        )

    def is_available(self) -> bool:
        if not self.is_banned:
            return True
        if time.time() >= self.ban_until:
            self.is_banned = False
            logger.info("Proxy %s ban expired, available again", self.context_name)
            return True
        return False


# ===================================================================
# ProxyPool — round-robin rotation + health tracking
# ===================================================================

class ProxyPool:
    """Round-robin proxy pool with health tracking and ban detection."""

    def __init__(self, proxies: list[str]) -> None:
        self._states: list[ProxyState] = []
        for i, url in enumerate(proxies):
            self._states.append(
                ProxyState(url=url.strip(), context_name=f"proxy_{i}")
            )
        self._index: int = 0

    @classmethod
    def from_env(cls) -> "ProxyPool":
        raw = os.environ.get("SCRAPING_PROXY_LIST", "")
        if not raw.strip():
            return cls([])
        proxies = [p.strip() for p in raw.split(",") if p.strip()]
        logger.info("ProxyPool loaded %d proxies from env", len(proxies))
        return cls(proxies)

    @classmethod
    def from_list(cls, proxies: list[str]) -> "ProxyPool":
        return cls(proxies)

    @property
    def is_empty(self) -> bool:
        return len(self._states) == 0

    @property
    def size(self) -> int:
        return len(self._states)

    @property
    def states(self) -> list[ProxyState]:
        return self._states

    def get_next_proxy(self) -> ProxyState | None:
        """Get next available proxy via round-robin. Returns None if all banned."""
        if self.is_empty:
            return None
        for _ in range(len(self._states)):
            state = self._states[self._index % len(self._states)]
            self._index += 1
            if state.is_available():
                return state
        return None

    def get_proxy_by_context(self, context_name: str) -> ProxyState | None:
        for state in self._states:
            if state.context_name == context_name:
                return state
        return None

    def report_success(self, proxy: ProxyState) -> None:
        proxy.mark_success()

    def report_ban(
        self,
        proxy: ProxyState,
        cooldown_base: float = 30.0,
        max_cooldown: float = 600.0,
    ) -> None:
        proxy.mark_failure(cooldown_base, max_cooldown)


# ===================================================================
# PlaywrightProxyMiddleware — Scrapy downloader middleware
# ===================================================================

class PlaywrightProxyMiddleware:
    """Assigns Playwright contexts with proxies.

    Supports rotating proxies (DataImpulse) and static proxies (WebShare).
    Set SCRAPING_PROXY_TYPE=rotating in .env for rotating proxy gateways.
    """

    def __init__(
        self, proxy_pool: ProxyPool, cooldown_base: float, max_cooldown: float,
        ban_threshold: int = 1, is_rotating: bool = False,
    ) -> None:
        self.pool = proxy_pool
        self.cooldown_base = cooldown_base
        self.max_cooldown = max_cooldown
        self.ban_threshold = ban_threshold
        self._is_rotating = is_rotating
        self._sessions: dict[str, str] = {}
        self._proxy_context_kwargs: dict[str, dict] = {}
        # For rotating: use ONE context name, never ban
        self._rotating_context = "proxy_rotating"
        # Log spam prevention
        self._all_banned_logged = False

    @classmethod
    def from_crawler(cls, crawler):
        from common.app_settings import ScrapingConfig

        # CLI --proxy-list override takes priority
        proxy_list_override = crawler.settings.get("PROXY_LIST_OVERRIDE")
        if proxy_list_override:
            proxies = [p.strip() for p in proxy_list_override.split(",") if p.strip()]
            pool = ProxyPool.from_list(proxies)
        else:
            pool = ProxyPool.from_env()

        cooldown_base = ScrapingConfig.proxy_ban_cooldown_base()
        max_cooldown = ScrapingConfig.proxy_ban_max_cooldown()
        ban_threshold = ScrapingConfig.proxy_ban_threshold()

        # Detect rotating proxy mode
        proxy_type = os.environ.get("SCRAPING_PROXY_TYPE", "static").strip().lower()
        is_rotating = (proxy_type == "rotating")

        middleware = cls(
            pool, cooldown_base, max_cooldown, ban_threshold,
            is_rotating=is_rotating,
        )

        if pool.is_empty:
            logger.info(
                "PlaywrightProxyMiddleware: no proxies configured, "
                "falling back to direct requests"
            )
        elif is_rotating:
            # Rotating mode: ONE context that routes through the gateway
            # The gateway (DataImpulse etc.) assigns a different IP per connection
            proxy_state = pool.states[0]
            proxy_dict = _parse_proxy_url(proxy_state.url)
            middleware._proxy_context_kwargs[middleware._rotating_context] = {
                **_BASE_CONTEXT_KWARGS,
                "proxy": proxy_dict,
            }
            logger.info(
                "PlaywrightProxyMiddleware: ROTATING mode — "
                "gateway=%s, no banning, CAPTCHA = skip & continue",
                proxy_dict.get("server", "?"),
            )
        else:
            # Static mode: one context per proxy
            active_count = 0
            max_active = 3
            for state in pool.states:
                if active_count >= max_active:
                    break
                ctx_kwargs = {**_BASE_CONTEXT_KWARGS}
                ctx_kwargs["proxy"] = _parse_proxy_url(state.url)
                middleware._proxy_context_kwargs[state.context_name] = ctx_kwargs
                active_count += 1
            logger.info(
                "PlaywrightProxyMiddleware: %d proxies loaded, %d active contexts (max %d)",
                pool.size, active_count, max_active,
            )

        # Connect spider_closed signal for stats
        crawler.signals.connect(
            middleware.spider_closed,
            signal=scrapy.signals.spider_closed,
        )

        return middleware

    # ------------------------------------------------------------------
    # process_request
    # ------------------------------------------------------------------

    def process_request(self, request, spider):
        if not request.meta.get("playwright"):
            return None
        if self.pool.is_empty:
            return None

        if self._is_rotating:
            return self._process_rotating_request(request)
        else:
            return self._process_static_request(request)

    def _process_rotating_request(self, request):
        """Rotating proxy: use a single context, never ban."""
        context_name = self._rotating_context

        request.meta["playwright_context"] = context_name
        request.meta["_proxy_context_name"] = context_name
        if context_name in self._proxy_context_kwargs:
            request.meta["playwright_context_kwargs"] = (
                self._proxy_context_kwargs[context_name]
            )
        return None

    def _process_static_request(self, request):
        """Static proxies: round-robin with session stickiness."""
        # Session stickiness
        session_key = request.meta.get("proxy_session")
        if session_key and session_key in self._sessions:
            context_name = self._sessions[session_key]
            proxy = self.pool.get_proxy_by_context(context_name)
            if proxy and proxy.is_available():
                request.meta["playwright_context"] = context_name
                request.meta["_proxy_context_name"] = context_name
                if context_name in self._proxy_context_kwargs:
                    request.meta["playwright_context_kwargs"] = (
                        self._proxy_context_kwargs[context_name]
                    )
                self._all_banned_logged = False
                return None
            del self._sessions[session_key]

        # Round-robin
        proxy = self.pool.get_next_proxy()
        if proxy is None:
            # Log once, not every request
            if not self._all_banned_logged:
                shortest = 0.0
                for s in self.pool.states:
                    if s.is_banned and s.ban_until > time.time():
                        remaining = s.ban_until - time.time()
                        if shortest == 0.0 or remaining < shortest:
                            shortest = remaining
                logger.warning(
                    "All %d proxies banned. Next recovery in %.0fs. "
                    "Requests fall through to default context.",
                    self.pool.size, shortest,
                )
                self._all_banned_logged = True
            return None

        self._all_banned_logged = False
        request.meta["playwright_context"] = proxy.context_name
        request.meta["_proxy_context_name"] = proxy.context_name
        if proxy.context_name in self._proxy_context_kwargs:
            request.meta["playwright_context_kwargs"] = (
                self._proxy_context_kwargs[proxy.context_name]
            )

        if session_key:
            self._sessions[session_key] = proxy.context_name

        return None

    # ------------------------------------------------------------------
    # process_response
    # ------------------------------------------------------------------

    def process_response(self, request, response, spider):
        context_name = request.meta.get("_proxy_context_name")
        if not context_name:
            return response

        if self._is_rotating:
            return self._process_rotating_response(request, response)
        else:
            return self._process_static_response(request, response)

    def _process_rotating_response(self, request, response):
        """Rotating proxy: track stats, NEVER ban. Mark CAPTCHA for spider."""
        proxy = self.pool.states[0]

        is_captcha = False

        if response.status in BAN_STATUS_CODES:
            is_captcha = True

        if not is_captcha and response.status == 200:
            body_prefix = response.body[:5000].lower()
            if any(marker in body_prefix for marker in CAPTCHA_MARKERS):
                is_captcha = True

        proxy.total_requests += 1
        if is_captcha:
            proxy.total_failures += 1
            # Set meta flag so the spider can check and skip immediately
            response.meta["_rotating_proxy_captcha"] = True
            logger.info(
                "Rotating proxy CAPTCHA/block (HTTP %d) on %s — "
                "skip this page (%d/%d = %.0f%% fail rate)",
                response.status,
                request.url[:80],
                proxy.total_failures,
                proxy.total_requests,
                (proxy.total_failures / proxy.total_requests * 100)
                if proxy.total_requests > 0 else 0,
            )
        # NO banning. Ever. The next request gets a fresh IP.

        return response

    def _process_static_response(self, request, response):
        """Static proxies: ban on failures with exponential backoff."""
        context_name = request.meta.get("_proxy_context_name")
        proxy = self.pool.get_proxy_by_context(context_name)
        if not proxy:
            return response

        is_ban = False

        if response.status in BAN_STATUS_CODES:
            is_ban = True
            logger.info(
                "Ban signal: HTTP %d on %s via %s",
                response.status, request.url[:80], context_name,
            )

        if not is_ban and response.status == 200:
            body_prefix = response.body[:5000].lower()
            if any(marker in body_prefix for marker in CAPTCHA_MARKERS):
                is_ban = True
                logger.info(
                    "Ban signal: CAPTCHA on %s via %s",
                    request.url[:80], context_name,
                )

        if is_ban:
            proxy.consecutive_failures += 1
            proxy.total_failures += 1
            proxy.total_requests += 1
            if proxy.consecutive_failures >= self.ban_threshold:
                cooldown = min(
                    self.cooldown_base * (2 ** (proxy.consecutive_failures - self.ban_threshold)),
                    self.max_cooldown,
                )
                cooldown *= 1 + random.uniform(-0.2, 0.2)
                proxy.ban_until = time.time() + cooldown
                proxy.is_banned = True
                logger.warning(
                    "Proxy %s banned for %.0fs (failures: %d, threshold: %d)",
                    context_name, cooldown,
                    proxy.consecutive_failures, self.ban_threshold,
                )
                to_remove = [
                    k for k, v in self._sessions.items() if v == context_name
                ]
                for k in to_remove:
                    del self._sessions[k]
        else:
            self.pool.report_success(proxy)

        return response

    # ------------------------------------------------------------------
    # process_exception
    # ------------------------------------------------------------------

    def process_exception(self, request, exception, spider):
        context_name = request.meta.get("_proxy_context_name")
        if not context_name:
            return None

        if self._is_rotating:
            # Rotating: just log, don't ban
            proxy = self.pool.states[0] if self.pool.states else None
            if proxy:
                proxy.total_requests += 1
                proxy.total_failures += 1
                logger.info(
                    "Rotating proxy exception: %s on %s",
                    type(exception).__name__, request.url[:60],
                )
            return None

        # Static: track and maybe ban
        proxy = self.pool.get_proxy_by_context(context_name)
        if proxy:
            proxy.consecutive_failures += 1
            proxy.total_failures += 1
            proxy.total_requests += 1
            if proxy.consecutive_failures >= self.ban_threshold:
                cooldown = min(
                    self.cooldown_base * (2 ** (proxy.consecutive_failures - self.ban_threshold)),
                    self.max_cooldown,
                )
                cooldown *= 1 + random.uniform(-0.2, 0.2)
                proxy.ban_until = time.time() + cooldown
                proxy.is_banned = True
                logger.warning(
                    "Proxy %s banned for %.0fs after exception (failures: %d)",
                    context_name, cooldown, proxy.consecutive_failures,
                )
        return None

    # ------------------------------------------------------------------
    # Spider closed — log stats
    # ------------------------------------------------------------------

    def spider_closed(self, spider, reason):
        if self.pool.is_empty:
            return
        logger.info("=== Proxy Stats ===")
        for state in self.pool.states:
            if state.total_requests > 0:
                success = state.total_requests - state.total_failures
                rate = (success / state.total_requests) * 100
                logger.info(
                    "  %s: %d requests, %d OK, %d failed (%.0f%% success)%s",
                    state.context_name,
                    state.total_requests,
                    success,
                    state.total_failures,
                    rate,
                    " [ROTATING]" if self._is_rotating else "",
                )


# ===================================================================
# Helpers
# ===================================================================

def _parse_proxy_url(proxy_url: str) -> dict:
    """Convert a proxy URL to Playwright's proxy dict format."""
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
    """Retry middleware with non-blocking exponential backoff."""

    BACKOFF_BASE = 5
    BACKOFF_MAX = 60
    BACKOFF_JITTER = 0.3

    def _add_backoff(self, result, request, spider):
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