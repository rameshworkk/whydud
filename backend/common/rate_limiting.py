"""Redis-backed rate limiting middleware and DRF throttle classes.

Uses token-bucket algorithm via Redis.  Falls back gracefully when Redis
is unavailable (passes request through to avoid hard-failure during outages).
"""
import hashlib
import time
from typing import Any

from django.conf import settings
from django.core.cache import cache
from rest_framework.throttling import BaseThrottle
from rest_framework.request import Request
from rest_framework.views import APIView


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_key(scope: str, ident: str) -> str:
    """Build a safe Redis key for rate-limit bucket."""
    hashed = hashlib.sha256(ident.encode()).hexdigest()[:16]
    return f"rl:{scope}:{hashed}"


def _is_allowed(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """
    Sliding-window counter using Redis.

    Returns (allowed, remaining_requests).
    """
    try:
        pipe = cache.client.get_client().pipeline()  # type: ignore[attr-defined]
        now = int(time.time())
        window_start = now - window_seconds

        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {f"{now}-{id(pipe)}": now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        _, _, count, _ = pipe.execute()

        remaining = max(0, limit - count)
        return count <= limit, remaining
    except Exception:
        # Redis unavailable — fail open
        return True, limit


# ---------------------------------------------------------------------------
# DRF Throttle classes (plug into REST_FRAMEWORK['DEFAULT_THROTTLE_CLASSES'])
# ---------------------------------------------------------------------------

class AnonSearchThrottle(BaseThrottle):
    """10 search requests/min for unauthenticated users."""
    scope = "anon_search"
    limit = 10
    window = 60

    def get_ident(self, request: Request) -> str:  # type: ignore[override]
        return self.get_ident(request) if False else (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("REMOTE_ADDR", "unknown")
        )

    def allow_request(self, request: Request, view: APIView) -> bool:
        if request.user and request.user.is_authenticated:
            return True
        ident = (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("REMOTE_ADDR", "unknown")
        )
        key = _make_key(self.scope, ident)
        allowed, self._remaining = _is_allowed(key, self.limit, self.window)
        return allowed

    def wait(self) -> float:
        return float(self.window)


class UserSearchThrottle(BaseThrottle):
    """30 search requests/min for authenticated users (60 for premium)."""
    scope = "user_search"
    window = 60

    def allow_request(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return True  # handled by AnonSearchThrottle
        tier = getattr(request.user, "subscription_tier", "free")
        limit = 60 if tier == "premium" else 30
        key = _make_key(self.scope, str(request.user.pk))
        allowed, self._remaining = _is_allowed(key, limit, self.window)
        return allowed

    def wait(self) -> float:
        return float(self.window)


class ProductViewThrottle(BaseThrottle):
    """20/min anon, 60/min registered, 120/min premium."""
    scope = "product_view"
    window = 60

    def allow_request(self, request: Request, view: APIView) -> bool:
        if request.user and request.user.is_authenticated:
            tier = getattr(request.user, "subscription_tier", "free")
            limit = 120 if tier == "premium" else 60
            ident = str(request.user.pk)
        else:
            limit = 20
            ident = (
                request.META.get("HTTP_CF_CONNECTING_IP")
                or request.META.get("REMOTE_ADDR", "unknown")
            )
        key = _make_key(self.scope, ident)
        allowed, self._remaining = _is_allowed(key, limit, self.window)
        return allowed

    def wait(self) -> float:
        return float(self.window)


class WriteThrottle(BaseThrottle):
    """Throttle for write operations (reviews, votes, discussions).

    Per-user, per-scope, per-day limits.
    """
    scope = "write"
    window = 86400  # 24 hours

    # Limits keyed by (action, tier) → int
    LIMITS: dict[str, dict[str, int]] = {
        "review": {"free": 3, "premium": 10},
        "vote": {"free": 50, "premium": 100},
        "thread": {"free": 5, "premium": 10},
        "reply": {"free": 20, "premium": 50},
        "tco_calc": {"free": 20, "premium": 999},
    }

    def __init__(self, action: str = "write"):
        self.action = action

    def allow_request(self, request: Request, view: APIView) -> bool:
        if not (request.user and request.user.is_authenticated):
            return False  # authenticated required for writes
        tier = getattr(request.user, "subscription_tier", "free")
        limits = self.LIMITS.get(self.action, {"free": 10, "premium": 50})
        limit = limits.get(tier, limits["free"])
        key = _make_key(f"{self.scope}:{self.action}", str(request.user.pk))
        allowed, self._remaining = _is_allowed(key, limit, self.window)
        return allowed

    def wait(self) -> float:
        return float(self.window)


# ---------------------------------------------------------------------------
# Django middleware (optional, for global rate limiting before DRF)
# ---------------------------------------------------------------------------

class RateLimitMiddleware:
    """Django middleware: global per-IP rate limiting at the edge.

    Applied before DRF throttling for hard protection against floods.
    Limit: 300 req/min per IP — far above any legitimate use.
    """
    LIMIT = 300
    WINDOW = 60

    def __init__(self, get_response: Any) -> None:
        self.get_response = get_response

    def __call__(self, request: Any) -> Any:
        # Skip for health checks and static assets
        path = request.path
        if path.startswith("/static/") or path == "/health/":
            return self.get_response(request)

        ip = (
            request.META.get("HTTP_CF_CONNECTING_IP")
            or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0].strip()
            or request.META.get("REMOTE_ADDR", "unknown")
        )
        key = _make_key("global", ip)
        allowed, remaining = _is_allowed(key, self.LIMIT, self.WINDOW)

        if not allowed:
            from django.http import JsonResponse
            return JsonResponse(
                {
                    "success": False,
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Please slow down.",
                    },
                },
                status=429,
            )

        response = self.get_response(request)
        response["X-RateLimit-Remaining"] = str(remaining)
        return response
