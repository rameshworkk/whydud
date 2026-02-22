"""Auth URL patterns for /api/v1/auth/ and /api/v1/me"""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="auth-register"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    # /api/v1/me (registered under auth prefix for simplicity)
    path("../me", views.MeView.as_view(), name="me"),
    # @whyd.xyz email
    path("../email/whydud/create", views.WhydudEmailView.as_view(), name="whydud-email-create"),
    path("../email/whydud/check-availability", views.WhydudEmailAvailabilityView.as_view(), name="whydud-email-check"),
    path("../email/whydud/status", views.WhydudEmailView.as_view(), name="whydud-email-status"),
    # Card vault
    path("../cards", views.PaymentMethodListCreateView.as_view(), name="cards-list"),
    path("../cards/<str:pk>", views.PaymentMethodDetailView.as_view(), name="cards-detail"),
]
