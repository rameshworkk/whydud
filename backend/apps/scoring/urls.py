from django.urls import path
from . import views

urlpatterns = [
    path("scoring/config", views.ActiveDudScoreConfigView.as_view(), name="scoring-config"),
]
