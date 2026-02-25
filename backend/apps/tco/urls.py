from django.urls import path
from . import views

urlpatterns = [
    path("tco/cities", views.CityListView.as_view(), name="tco-cities"),
    path("tco/models/<slug:category_slug>", views.TCOModelView.as_view(), name="tco-model"),
    path("tco/calculate", views.TCOCalculateView.as_view(), name="tco-calculate"),
    path("tco/compare", views.TCOCompareView.as_view(), name="tco-compare"),
    path("tco/profile", views.TCOProfileView.as_view(), name="tco-profile"),
]
