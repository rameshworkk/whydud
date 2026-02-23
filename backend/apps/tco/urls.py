from django.urls import path
from . import views

urlpatterns = [
    path("tco/cities", views.CityListView.as_view(), name="tco-cities"),
    path("tco/models/<slug:category_slug>", views.TCOModelView.as_view(), name="tco-model"),
    path("tco/profile", views.TCOProfileView.as_view(), name="tco-profile"),
]
