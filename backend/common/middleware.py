"""Custom middleware for the Whydud backend."""

from __future__ import annotations

import uuid

import structlog
from django.http import HttpRequest, HttpResponse


class RequestIDMiddleware:
    """Generate a unique request ID per request and bind it to structlog context.

    If the incoming request already carries an ``X-Request-ID`` header (e.g.
    from a reverse proxy like Caddy), that value is reused.  Otherwise a new
    UUID-4 is generated.

    The ID is:
    * bound to :mod:`structlog` context-vars so every log line within the
      request automatically includes ``request_id``;
    * attached to the response as the ``X-Request-ID`` header for client
      correlation;
    * stored on ``request.META["HTTP_X_REQUEST_ID"]`` for downstream code.
    """

    HEADER = "X-Request-ID"

    def __init__(self, get_response: callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.META.get("HTTP_X_REQUEST_ID") or str(uuid.uuid4())

        # Store on the request for downstream access
        request.META["HTTP_X_REQUEST_ID"] = request_id

        # Bind to structlog context-vars (cleared automatically at end of
        # async context / thread-local scope).
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            service="backend",
        )

        response = self.get_response(request)
        response[self.HEADER] = request_id
        return response
