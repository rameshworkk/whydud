"""Shared pagination classes."""
from rest_framework.pagination import CursorPagination as _BaseCursorPagination
from rest_framework.response import Response


class CursorPagination(_BaseCursorPagination):
    """Cursor-based pagination. Use `cursor` query param."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100
    ordering = "-created_at"

    def get_paginated_response(self, data: list) -> Response:
        return Response(
            {
                "success": True,
                "data": data,
                "pagination": {
                    "next": self.get_next_link(),
                    "previous": self.get_previous_link(),
                },
            }
        )
