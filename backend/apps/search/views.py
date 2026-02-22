from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import AllowAny

class SearchView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "search"

    def get(self, request: Request) -> Response:
        # TODO Sprint 1 Week 3: query Meilisearch
        raise NotImplementedError

class AutocompleteView(APIView):
    permission_classes = [AllowAny]
    throttle_scope = "search"

    def get(self, request: Request) -> Response:
        # TODO Sprint 1 Week 3
        raise NotImplementedError

class AdhocScrapeView(APIView):
    """Trigger on-demand scrape for a product not in DB."""
    def post(self, request: Request) -> Response:
        # TODO Sprint 2 (P1)
        raise NotImplementedError
