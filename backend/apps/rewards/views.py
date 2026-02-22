from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

class RewardBalanceView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request: Request) -> Response:
        # TODO Sprint 4 Week 11
        raise NotImplementedError

class RewardHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class GiftCardCatalogView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request: Request) -> Response:
        raise NotImplementedError

class RedeemPointsView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request: Request) -> Response:
        raise NotImplementedError

class RedemptionHistoryView(APIView):
    permission_classes = [IsAuthenticated]
    def get(self, request: Request) -> Response:
        raise NotImplementedError
