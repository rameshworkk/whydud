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

    Uses print() to ensure output reaches Docker logs regardless of
    structlog configuration. Remove after the issue is resolved.
    """

    def __init__(self, get_response: callable) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        # Log ALL admin requests to verify middleware is active
        if request.path.startswith("/admin/"):
            import sys
            print(
                f"[ADMIN_DEBUG] {request.method} {request.path} "
                f"host={request.META.get('HTTP_HOST')}",
                file=sys.stderr, flush=True,
            )

        if request.path == "/admin/login/" and request.method == "POST":
            import sys
            username = request.POST.get("username", "<MISSING>")
            password = request.POST.get("password", "")
            has_csrf = bool(request.POST.get("csrfmiddlewaretoken"))
            csrf_cookie = bool(request.COOKIES.get("csrftoken"))
            session_cookie = bool(request.COOKIES.get("sessionid"))

            # Try authenticate directly
            auth_user = None
            try:
                auth_user = authenticate(
                    request,
                    username=username,
                    password=password,
                )
            except Exception as exc:
                print(f"[ADMIN_LOGIN_DEBUG] authenticate() EXCEPTION: {exc}", file=sys.stderr, flush=True)

            debug_info = (
                f"\n{'='*60}\n"
                f"[ADMIN_LOGIN_DEBUG] POST /admin/login/\n"
                f"  username       = {username!r}\n"
                f"  username_len   = {len(username)}\n"
                f"  has_password   = {bool(password)}\n"
                f"  password_len   = {len(password)}\n"
                f"  has_csrf_token = {has_csrf}\n"
                f"  has_csrf_cookie= {csrf_cookie}\n"
                f"  has_session    = {session_cookie}\n"
                f"  auth_result    = {'SUCCESS user=' + str(auth_user.pk) if auth_user else 'FAILED'}\n"
                f"  content_type   = {request.content_type}\n"
                f"  host           = {request.META.get('HTTP_HOST')}\n"
                f"  x_fwd_host    = {request.META.get('HTTP_X_FORWARDED_HOST')}\n"
                f"  x_fwd_proto   = {request.META.get('HTTP_X_FORWARDED_PROTO')}\n"
                f"  cf_ip          = {request.META.get('HTTP_CF_CONNECTING_IP')}\n"
                f"  cookie_names   = {list(request.COOKIES.keys())}\n"
                f"  post_keys      = {list(request.POST.keys())}\n"
                f"{'='*60}"
            )
            print(debug_info, file=sys.stderr, flush=True)

        response = self.get_response(request)
        return response
