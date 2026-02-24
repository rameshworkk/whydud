"""Auth URL patterns for /api/v1/auth/."""
from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("register", views.RegisterView.as_view(), name="auth-register"),
    path("login", views.LoginView.as_view(), name="auth-login"),
    path("logout", views.LogoutView.as_view(), name="auth-logout"),
    path("change-password", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("forgot-password", views.ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password", views.ResetPasswordView.as_view(), name="auth-reset-password"),
    path("verify-email", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification", views.ResendVerificationEmailView.as_view(), name="auth-resend-verification"),
    path("oauth/exchange-code", views.OAuthExchangeCodeView.as_view(), name="auth-oauth-exchange-code"),
]
