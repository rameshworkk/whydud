from django.urls import path
from . import views

urlpatterns = [
    path("offers/active", views.OffersActiveView.as_view(), name="offers-active"),

    # Price alerts
    path("alerts/price", views.CreatePriceAlertView.as_view(), name="alert-create"),
    path("alerts/triggered", views.TriggeredAlertsView.as_view(), name="alerts-triggered"),
    path("alerts", views.ListAlertsView.as_view(), name="alerts-list"),
    path("alerts/<str:pk>", views.AlertDetailView.as_view(), name="alert-detail"),

    # Affiliate click tracking
    path("clicks/track", views.TrackClickView.as_view(), name="click-track"),
    path("clicks/history", views.ClickHistoryView.as_view(), name="click-history"),
]
