from django.urls import path
from . import views

urlpatterns = [
    path("offers/active", views.OffersActiveView.as_view(), name="offers-active"),
    path("me/price-alerts", views.PriceAlertListCreateView.as_view(), name="price-alerts-list"),
    path("me/price-alerts/<str:pk>", views.PriceAlertDetailView.as_view(), name="price-alerts-detail"),
]
