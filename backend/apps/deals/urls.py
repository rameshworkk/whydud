from django.urls import path
from . import views

urlpatterns = [
    path("deals", views.DealListView.as_view(), name="deals-list"),
    path("deals/<uuid:pk>", views.DealDetailView.as_view(), name="deals-detail"),
    path("deals/<uuid:pk>/click", views.DealClickView.as_view(), name="deals-click"),
]
