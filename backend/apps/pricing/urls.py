from django.urls import path
from . import views

urlpatterns = [
    path("offers/active", views.ActiveOffersView.as_view(), name="offers-active"),
]
