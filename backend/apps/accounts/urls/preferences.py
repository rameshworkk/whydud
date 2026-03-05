"""Purchase preference URL patterns for /api/v1/preferences/."""
from django.urls import path

from apps.accounts import preference_views as views

urlpatterns = [
    # GET /preferences — list all user's category preferences
    path("preferences", views.PreferenceListView.as_view(), name="preference-list"),

    # GET /preferences/schemas — list all active category schemas (public)
    path("preferences/schemas", views.PreferenceSchemaListView.as_view(), name="preference-schema-list"),

    # GET /preferences/:category_slug/schema — questionnaire schema (public)
    path("preferences/<slug:category_slug>/schema", views.PreferenceSchemaView.as_view(), name="preference-schema"),

    # GET / POST / PATCH / DELETE /preferences/:category_slug
    path("preferences/<slug:category_slug>", views.PreferenceDetailView.as_view(), name="preference-detail"),
]
