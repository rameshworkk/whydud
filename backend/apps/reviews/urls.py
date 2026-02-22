from django.urls import path
from . import views

urlpatterns = [
    path("products/<slug:slug>/reviews", views.ProductReviewsView.as_view(), name="product-reviews"),
    path("reviews/<uuid:pk>/vote", views.ReviewVoteView.as_view(), name="review-vote"),
]
