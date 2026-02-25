"""Root URL configuration for Whydud backend."""
from django.contrib import admin
from django.urls import include, path

from apps.accounts.views import OAuthCompleteView

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # OAuth completion — AllAuth redirects here after Google login;
    # creates a one-time code and redirects to the frontend callback page.
    path("oauth/complete/", OAuthCompleteView.as_view(), name="oauth-complete"),

    # API v1
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
    path("api/v1/", include("apps.accounts.urls.account")),
    path("api/v1/", include("apps.accounts.urls.notifications")),
    path("api/v1/", include("apps.accounts.urls.preferences")),
    path("api/v1/", include("apps.products.urls")),
    path("api/v1/", include("apps.pricing.urls")),
    path("api/v1/", include("apps.reviews.urls")),
    path("api/v1/", include("apps.email_intel.urls")),
    path("api/v1/", include("apps.wishlists.urls")),
    path("api/v1/", include("apps.deals.urls")),
    path("api/v1/", include("apps.rewards.urls")),
    path("api/v1/", include("apps.discussions.urls")),
    path("api/v1/", include("apps.search.urls")),
    path("api/v1/", include("apps.scoring.urls")),
    path("api/v1/", include("apps.tco.urls")),

    # Webhooks (no /api/v1 prefix — matched by Caddy separately)
    path("webhooks/", include("apps.email_intel.urls.webhooks")),

    # AllAuth (social auth flows)
    path("accounts/", include("allauth.urls")),
]
