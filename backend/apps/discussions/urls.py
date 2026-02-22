from django.urls import path
from . import views

urlpatterns = [
    path("products/<slug:slug>/discussions", views.CreateDiscussionView.as_view(), name="discussions-create"),
    path("discussions/<uuid:pk>", views.DiscussionDetailView.as_view(), name="discussions-detail"),
    path("discussions/<uuid:pk>/replies", views.DiscussionReplyView.as_view(), name="discussions-replies"),
    path("discussions/<uuid:pk>/vote", views.DiscussionVoteView.as_view(), name="discussions-vote"),
    path("discussions/replies/<uuid:pk>/vote", views.ReplyVoteView.as_view(), name="replies-vote"),
    path("discussions/replies/<uuid:pk>/accept", views.ReplyAcceptView.as_view(), name="replies-accept"),
]
