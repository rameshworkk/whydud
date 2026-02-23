"""Shared pagination classes.

All page-size values are read from ``common.app_settings`` — never hardcoded.
Sprint 4 admin panel will expose those settings as editable SiteConfig rows.

Usage in a view::

    paginator = CursorPagination()
    page = paginator.paginate_queryset(qs, request)
    if page is not None:
        return paginator.get_paginated_response(serializer.data)

For product list pages (different default page size)::

    paginator = ProductListPagination()
    paginator.ordering = ["-dud_score", "id"]   # override per sort_by param
"""
from rest_framework.pagination import CursorPagination as _BaseCursorPagination
from rest_framework.response import Response

from common.app_settings import PaginationConfig, ProductConfig


class CursorPagination(_BaseCursorPagination):
    """General-purpose cursor pagination.

    Page size comes from ``PAGINATION_PAGE_SIZE`` / ``PAGINATION_MAX_PAGE_SIZE``
    settings.  Clients may request a smaller page via ``?page_size=N``.
    """

    page_size_query_param = "page_size"
    ordering = "-created_at"

    # Class-level sentinels so DRF introspection tooling sees a value.
    # Real values are supplied at request time by get_page_size() below.
    page_size = 20
    max_page_size = 100

    def get_page_size(self, request) -> int:
        """Return page size from settings, capped at max. No hardcoded magic."""
        max_size = PaginationConfig.max_page_size()
        if self.page_size_query_param:
            param = request.query_params.get(self.page_size_query_param)
            if param is not None:
                try:
                    requested = int(param)
                    if requested > 0:
                        return min(requested, max_size)
                except (ValueError, TypeError):
                    pass
        return min(PaginationConfig.page_size(), max_size)

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

    def get_paginated_response_schema(self, schema: dict) -> dict:
        """OpenAPI schema fragment for paginated responses."""
        return {
            "type": "object",
            "properties": {
                "success": {"type": "boolean"},
                "data": schema,
                "pagination": {
                    "type": "object",
                    "properties": {
                        "next": {"type": "string", "nullable": True},
                        "previous": {"type": "string", "nullable": True},
                    },
                },
            },
        }


class ProductListPagination(CursorPagination):
    """Cursor pagination tuned for the product list endpoint.

    Uses ``PRODUCT_LIST_PAGE_SIZE`` / ``PRODUCT_LIST_PAGE_SIZE_MAX`` so the
    product grid page size can be tuned independently of generic pagination.
    Views set ``paginator.ordering`` before calling ``paginate_queryset`` to
    match the requested sort_by param.
    """

    ordering = "-dud_score"

    def get_page_size(self, request) -> int:
        max_size = ProductConfig.max_page_size()
        if self.page_size_query_param:
            param = request.query_params.get(self.page_size_query_param)
            if param is not None:
                try:
                    requested = int(param)
                    if requested > 0:
                        return min(requested, max_size)
                except (ValueError, TypeError):
                    pass
        return min(ProductConfig.page_size(), max_size)
