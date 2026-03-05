"""Account URL patterns for /api/v1/ (me, cards, email)."""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    # Marketplace preferences
    path("me/marketplace-preferences", views.MarketplacePreferenceView.as_view(), name="marketplace-preferences"),
    # DPDP: account deletion, restoration, data export
    path("me/account", views.DeleteAccountView.as_view(), name="delete-account"),
    path("me/account/restore", views.RestoreAccountView.as_view(), name="restore-account"),
    path("me/export", views.ExportDataView.as_view(), name="export-data"),
    path("me/export/<str:task_id>", views.ExportStatusView.as_view(), name="export-status"),
    # Shopping email (whyd.in / whyd.click / whyd.shop)
    path("email/whydud/create", views.WhydudEmailView.as_view(), name="whydud-email-create"),
    path("email/whydud/check-availability", views.WhydudEmailAvailabilityView.as_view(), name="whydud-email-check"),
    path("email/whydud/status", views.WhydudEmailView.as_view(), name="whydud-email-status"),
    # Card vault
    path("cards", views.PaymentMethodListCreateView.as_view(), name="cards-list"),
    path("cards/<str:pk>", views.PaymentMethodDetailView.as_view(), name="cards-detail"),
]
