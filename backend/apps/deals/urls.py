from django.urls import path
from . import views

urlpatterns = [
    path("deals", views.DealListView.as_view(), name="deals-list"),
    path("deals/<str:pk>", views.DealDetailView.as_view(), name="deals-detail"),
    path("deals/<str:pk>/click", views.DealClickView.as_view(), name="deals-click"),
]
