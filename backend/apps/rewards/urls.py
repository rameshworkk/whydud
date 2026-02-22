from django.urls import path
from . import views

urlpatterns = [
    path("rewards/balance", views.RewardBalanceView.as_view(), name="rewards-balance"),
    path("rewards/history", views.RewardHistoryView.as_view(), name="rewards-history"),
    path("rewards/gift-cards", views.GiftCardCatalogView.as_view(), name="rewards-gift-cards"),
    path("rewards/redeem", views.RedeemPointsView.as_view(), name="rewards-redeem"),
    path("rewards/redemptions", views.RedemptionHistoryView.as_view(), name="rewards-redemptions"),
]
