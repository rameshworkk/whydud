"""Root URL configuration for Whydud backend."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    # Django admin
    path("admin/", admin.site.urls),

    # API v1
    path("api/v1/auth/", include("apps.accounts.urls.auth")),
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

    # Webhooks (no /api/v1 prefix — matched by Caddy separately)
    path("webhooks/", include("apps.email_intel.urls.webhooks")),

    # AllAuth (social auth flows)
    path("accounts/", include("allauth.urls")),
]
