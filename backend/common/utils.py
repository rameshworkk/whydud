"""Shared utility functions and helpers."""
from typing import Any

from rest_framework.response import Response
from rest_framework.views import exception_handler


def success_response(data: Any, status: int = 200) -> Response:
    """Wrap data in standard `{success: true, data: ...}` envelope."""
    return Response({"success": True, "data": data}, status=status)


def error_response(code: str, message: str, status: int = 400) -> Response:
    """Return standard `{success: false, error: {code, message}}` envelope."""
    return Response(
        {"success": False, "error": {"code": code, "message": message}},
        status=status,
    )


def custom_exception_handler(exc: Exception, context: dict) -> Response | None:
    """DRF exception handler that wraps errors in standard envelope."""
    response = exception_handler(exc, context)
    if response is not None:
        response.data = {
            "success": False,
            "error": {
                "code": "api_error",
                "message": str(response.data),
            },
        }
    return response
