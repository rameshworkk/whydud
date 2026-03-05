from django.urls import path
from . import views

urlpatterns = [
    path("scoring/config", views.ActiveDudScoreConfigView.as_view(), name="scoring-config"),

    # Brand Trust Scores
    path("brands/leaderboard", views.BrandLeaderboardView.as_view(), name="brand-leaderboard"),
    path("brands/<slug:slug>/trust-score", views.BrandTrustScoreView.as_view(), name="brand-trust-score"),
]
