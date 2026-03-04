"""DRF throttle classes scoped to specific endpoint groups.

Rates are configured in ``REST_FRAMEWORK['DEFAULT_THROTTLE_RATES']`` under
the matching ``scope`` key.  Standard DRF 429 responses with ``Retry-After``
header are returned automatically when limits are exceeded.
"""

from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AuthRateThrottle(UserRateThrottle):
    """Throttle for authentication endpoints (login, register, forgot-password).

    Uses IP for unauthenticated requests (which auth endpoints always are).
    Scope: ``auth`` — default 10/minute.
    """

    scope = "auth"

    def get_cache_key(self, request, view):
        # Auth endpoints are always unauthenticated, so key by IP.
        return self.cache_format % {
            "scope": self.scope,
            "ident": self.get_ident(request),
        }


class SearchRateThrottle(AnonRateThrottle):
    """Throttle for search and autocomplete endpoints.

    Scope: ``search`` — default 60/minute.
    """

    scope = "search"


class ReviewRateThrottle(UserRateThrottle):
    """Throttle for review creation.

    Scope: ``review`` — default 5/hour.
    """

    scope = "review"


class EmailSendThrottle(UserRateThrottle):
    """Throttle for sending emails from @whyd.xyz addresses.

    Scope: ``email_send`` — default 10/day.
    """

    scope = "email_send"
