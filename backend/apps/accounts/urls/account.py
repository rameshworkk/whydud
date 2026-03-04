"""Account URL patterns for /api/v1/ (me, cards, email)."""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("me", views.MeView.as_view(), name="me"),
    # Marketplace preferences
    path("me/marketplace-preferences", views.MarketplacePreferenceView.as_view(), name="marketplace-preferences"),
    # @whyd.xyz email
    path("email/whydud/create", views.WhydudEmailView.as_view(), name="whydud-email-create"),
    path("email/whydud/check-availability", views.WhydudEmailAvailabilityView.as_view(), name="whydud-email-check"),
    path("email/whydud/status", views.WhydudEmailView.as_view(), name="whydud-email-status"),
    # Card vault
    path("cards", views.PaymentMethodListCreateView.as_view(), name="cards-list"),
    path("cards/<str:pk>", views.PaymentMethodDetailView.as_view(), name="cards-detail"),
]
