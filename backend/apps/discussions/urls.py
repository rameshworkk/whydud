from django.urls import path
from . import views

urlpatterns = [
    path("discussions/<str:pk>", views.ThreadDetailView.as_view(), name="discussion-detail"),
    path("discussions/<str:pk>/replies", views.ThreadReplyCreateView.as_view(), name="discussion-replies"),
    path("discussions/<str:pk>/vote", views.ThreadVoteView.as_view(), name="discussion-vote"),
    path("discussions/replies/<str:pk>/vote", views.ReplyVoteView.as_view(), name="reply-vote"),
    path("discussions/replies/<str:pk>/accept", views.ReplyAcceptView.as_view(), name="reply-accept"),
]
