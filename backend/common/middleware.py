"""Custom middleware for the Whydud backend."""

from __future__ import annotations

import uuid

import structlog
from django.contrib.auth import authenticate
from django.http import HttpRequest, HttpResponse

logger = structlog.get_logger(__name__)


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


class AdminLoginDebugMiddleware:
    """Temporary middleware to diagnose admin login failures.

    Logs POST data, headers, and auth result for /admin/login/ requests.
    Remove after the issue is resolved.
    """

    def __init__(self, get_response: callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        if request.path == "/admin/login/" and request.method == "POST":
            username = request.POST.get("username", "<MISSING>")
            has_password = bool(request.POST.get("password"))
            has_csrf = bool(request.POST.get("csrfmiddlewaretoken"))
            csrf_cookie = bool(request.COOKIES.get("csrftoken"))
            session_cookie = bool(request.COOKIES.get("sessionid"))

            # Try authenticate directly to see the result
            auth_user = None
            if username != "<MISSING>" and has_password:
                auth_user = authenticate(
                    request,
                    username=username,
                    password=request.POST.get("password"),
                )

            logger.warning(
                "ADMIN_LOGIN_DEBUG",
                username=username,
                username_repr=repr(username),
                username_len=len(username) if username else 0,
                has_password=has_password,
                password_len=len(request.POST.get("password", "")),
                has_csrf_token=has_csrf,
                has_csrf_cookie=csrf_cookie,
                has_session_cookie=session_cookie,
                auth_result="SUCCESS" if auth_user else "FAILED",
                auth_user_id=str(auth_user.pk) if auth_user else None,
                content_type=request.content_type,
                cf_connecting_ip=request.META.get("HTTP_CF_CONNECTING_IP"),
                x_forwarded_for=request.META.get("HTTP_X_FORWARDED_FOR"),
                x_forwarded_proto=request.META.get("HTTP_X_FORWARDED_PROTO"),
                x_forwarded_host=request.META.get("HTTP_X_FORWARDED_HOST"),
                host=request.META.get("HTTP_HOST"),
                referer=request.META.get("HTTP_REFERER"),
                origin=request.META.get("HTTP_ORIGIN"),
                cookie_count=len(request.COOKIES),
                cookie_names=list(request.COOKIES.keys()),
            )

        response = self.get_response(request)
        return response
