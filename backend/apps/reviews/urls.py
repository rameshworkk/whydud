from django.urls import path
from . import views

urlpatterns = [
    # GET  /products/:slug/reviews — list product reviews (public)
    # POST /products/:slug/reviews — submit review (authenticated)
    path("products/<slug:slug>/reviews", views.ProductReviewsView.as_view(), name="product-reviews"),

    # GET /products/:slug/review-features — category-specific feature rating keys
    path("products/<slug:slug>/review-features", views.ReviewFeaturesView.as_view(), name="review-features"),

    # POST /reviews/:id/vote — upvote/downvote
    # DELETE /reviews/:id/vote — remove vote
    path("reviews/<str:pk>/vote", views.ReviewVoteView.as_view(), name="review-vote"),

    # POST /reviews/:id/purchase-proof — upload invoice image
    path("reviews/<str:pk>/purchase-proof", views.UploadPurchaseProofView.as_view(), name="upload-purchase-proof"),

    # PATCH /reviews/:id — edit own review
    # DELETE /reviews/:id — delete own review
    path("reviews/<str:pk>", views.ReviewDetailView.as_view(), name="review-detail"),

    # GET /me/reviews — list user's own reviews
    path("me/reviews", views.MyReviewsView.as_view(), name="my-reviews"),

    # GET /me/reviewer-profile — user's level, stats, badges
    path("me/reviewer-profile", views.MyReviewerProfileView.as_view(), name="my-reviewer-profile"),

    # GET /leaderboard/reviewers — top reviewers this week
    path("leaderboard/reviewers", views.LeaderboardView.as_view(), name="leaderboard-reviewers"),

    # GET /leaderboard/reviewers/:category_slug — top reviewers per category
    path("leaderboard/reviewers/<slug:category_slug>", views.CategoryLeaderboardView.as_view(), name="leaderboard-reviewers-category"),
]
