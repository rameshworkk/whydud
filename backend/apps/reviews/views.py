"""Review views."""
import os
import uuid

from django.core.files.storage import default_storage
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.throttling import ReviewRateThrottle
from common.utils import error_response, success_response

from .models import Review, ReviewerProfile, ReviewVote
from .serializers import (
    MyReviewsSerializer,
    ReviewerProfileSerializer,
    ReviewSerializer,
    ReviewVoteSerializer,
    WriteReviewSerializer,
)


class ProductReviewsView(APIView):
    """GET  /products/:slug/reviews — list reviews (public).
    POST /products/:slug/reviews — submit review (authenticated).
    """

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    def get_throttles(self):
        if self.request.method == "POST":
            return [ReviewRateThrottle()]
        return []

    def get(self, request: Request, slug: str) -> Response:
        from apps.products.models import Product

        product = get_object_or_404(Product, slug=slug)
        sort = request.query_params.get("sort", "helpful")
        rating = request.query_params.get("rating")
        verified_only = request.query_params.get("verified") == "1"
        source_filter = request.query_params.get("source")  # marketplace slug or "whydud"

        qs = Review.objects.filter(product=product, is_flagged=False).select_related(
            "listing__marketplace", "marketplace"
        )

        if rating:
            try:
                qs = qs.filter(rating=int(rating))
            except ValueError:
                pass
        if verified_only:
            qs = qs.filter(is_verified_purchase=True)
        if source_filter:
            if source_filter == "whydud":
                qs = qs.filter(source=Review.Source.WHYDUD)
            else:
                qs = qs.filter(marketplace__slug=source_filter)

        sort_map = {
            "helpful": "-helpful_vote_count",
            "recent": "-review_date",
            "rating_asc": "rating",
            "rating_desc": "-rating",
        }
        qs = qs.order_by(sort_map.get(sort, "-helpful_vote_count"))

        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ReviewSerializer(page, many=True, context={"request": request}).data
            )
        return success_response(ReviewSerializer(qs, many=True, context={"request": request}).data)

    def post(self, request: Request, slug: str) -> Response:
        """Submit a new review with 48hr publish hold."""
        from apps.products.models import Product

        product = get_object_or_404(Product, slug=slug)
        serializer = WriteReviewSerializer(
            data=request.data,
            context={"request": request, "product": product},
        )
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        review = serializer.save()
        return success_response(MyReviewsSerializer(review).data, status=201)


class ReviewVoteView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request: Request, pk: str) -> Response:
        review = get_object_or_404(Review, pk=pk)
        serializer = ReviewVoteSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        vote_value: int = serializer.validated_data["vote"]
        existing = ReviewVote.objects.filter(review=review, user=request.user).first()

        if existing:
            if existing.vote == vote_value:
                return error_response("already_voted", "You already cast this vote.")
            old = existing.vote
            existing.vote = vote_value
            existing.save(update_fields=["vote"])
            # Swap the counters
            if old == 1:
                Review.objects.filter(pk=pk).update(
                    upvotes=F("upvotes") - 1,
                    downvotes=F("downvotes") + 1,
                    vote_score=F("vote_score") - 2,
                )
            else:
                Review.objects.filter(pk=pk).update(
                    upvotes=F("upvotes") + 1,
                    downvotes=F("downvotes") - 1,
                    vote_score=F("vote_score") + 2,
                )
        else:
            ReviewVote.objects.create(review=review, user=request.user, vote=vote_value)
            if vote_value == 1:
                Review.objects.filter(pk=pk).update(
                    upvotes=F("upvotes") + 1,
                    vote_score=F("vote_score") + 1,
                )
            else:
                Review.objects.filter(pk=pk).update(
                    downvotes=F("downvotes") + 1,
                    vote_score=F("vote_score") - 1,
                )

        return success_response({"vote": vote_value})

    @transaction.atomic
    def delete(self, request: Request, pk: str) -> Response:
        review = get_object_or_404(Review, pk=pk)
        vote_obj = ReviewVote.objects.filter(review=review, user=request.user).first()
        if not vote_obj:
            return error_response("not_found", "No vote to remove.", status=404)

        if vote_obj.vote == 1:
            Review.objects.filter(pk=pk).update(
                upvotes=F("upvotes") - 1,
                vote_score=F("vote_score") - 1,
            )
        else:
            Review.objects.filter(pk=pk).update(
                downvotes=F("downvotes") - 1,
                vote_score=F("vote_score") + 1,
            )

        vote_obj.delete()
        return success_response({"detail": "Vote removed."})


class ReviewDetailView(APIView):
    """PATCH /reviews/:id — edit own review.
    DELETE /reviews/:id — delete own review.
    """

    permission_classes = [IsAuthenticated]

    EDITABLE_FIELDS = {
        "rating", "title", "body_positive", "body_negative",
        "nps_score", "feature_ratings",
        "purchase_platform", "purchase_seller",
        "purchase_delivery_date", "purchase_price_paid",
        "seller_delivery_rating", "seller_packaging_rating",
        "seller_accuracy_rating", "seller_communication_rating",
    }

    def patch(self, request: Request, pk: str) -> Response:
        review = get_object_or_404(Review, pk=pk)
        if review.user_id != request.user.id:
            return error_response("forbidden", "You can only edit your own reviews.", status=403)

        updated_fields = []
        for field, value in request.data.items():
            if field in self.EDITABLE_FIELDS:
                setattr(review, field, value)
                updated_fields.append(field)

        if not updated_fields:
            return error_response("validation_error", "No valid fields provided.")

        if "rating" in updated_fields and not (1 <= review.rating <= 5):
            return error_response("validation_error", "Rating must be between 1 and 5.")

        review.save(update_fields=updated_fields + ["updated_at"])
        return success_response(MyReviewsSerializer(review).data)

    def delete(self, request: Request, pk: str) -> Response:
        review = get_object_or_404(Review, pk=pk)
        if review.user_id != request.user.id:
            return error_response("forbidden", "You can only delete your own reviews.", status=403)
        review.delete()
        return success_response({"detail": "Review deleted."})


class MyReviewsView(APIView):
    """GET /api/v1/me/reviews — list the authenticated user's reviews."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = (
            Review.objects.filter(user=request.user)
            .select_related("product")
            .order_by("-created_at")
        )
        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                MyReviewsSerializer(page, many=True).data
            )
        return success_response(MyReviewsSerializer(qs, many=True).data)


class ReviewFeaturesView(APIView):
    """GET /api/v1/products/:slug/review-features — category-specific feature rating keys."""

    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        from apps.products.models import Product

        product = get_object_or_404(Product, slug=slug)
        category = product.category
        if not category or not category.spec_schema:
            return success_response({"features": []})

        features = category.spec_schema.get("review_features", [])
        return success_response({"features": features})


ALLOWED_PROOF_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_PROOF_SIZE = 5 * 1024 * 1024  # 5 MB


class UploadPurchaseProofView(APIView):
    """POST /api/v1/reviews/:id/purchase-proof — upload invoice/receipt image."""

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    def post(self, request: Request, pk: str) -> Response:
        review = get_object_or_404(Review, pk=pk)
        if review.user_id != request.user.id:
            return error_response("forbidden", "You can only upload proof for your own reviews.", status=403)

        file = request.FILES.get("file")
        if not file:
            return error_response("validation_error", "No file provided.")

        if file.content_type not in ALLOWED_PROOF_TYPES:
            return error_response(
                "validation_error",
                "File must be JPEG, PNG, or PDF.",
            )

        if file.size > MAX_PROOF_SIZE:
            return error_response(
                "validation_error",
                "File must be 5 MB or smaller.",
            )

        ext = os.path.splitext(file.name)[1] or ".bin"
        filename = f"{uuid.uuid4().hex}{ext}"
        save_path = f"review-proofs/{review.pk}/{filename}"
        saved = default_storage.save(save_path, file)

        review.has_purchase_proof = True
        review.purchase_proof_url = saved
        review.save(update_fields=["has_purchase_proof", "purchase_proof_url", "updated_at"])

        return success_response(MyReviewsSerializer(review).data)


class MyReviewerProfileView(APIView):
    """GET /api/v1/me/reviewer-profile — user's level, stats, badges."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        profile, _ = ReviewerProfile.objects.get_or_create(user=request.user)
        return success_response(ReviewerProfileSerializer(profile).data)


class LeaderboardView(APIView):
    """GET /api/v1/leaderboard/reviewers — top reviewers this week."""

    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        qs = (
            ReviewerProfile.objects.filter(is_top_reviewer=True)
            .select_related("user")
            .order_by("leaderboard_rank")
        )
        paginator = CursorPagination()
        paginator.ordering = "leaderboard_rank"
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ReviewerProfileSerializer(page, many=True).data
            )
        return success_response(ReviewerProfileSerializer(qs, many=True).data)


class CategoryLeaderboardView(APIView):
    """GET /api/v1/leaderboard/reviewers/:category_slug — top reviewers per category."""

    permission_classes = [AllowAny]

    def get(self, request: Request, category_slug: str) -> Response:
        from apps.products.models import Category

        category = get_object_or_404(Category, slug=category_slug)
        user_ids = (
            Review.objects.filter(product__category=category, user__isnull=False)
            .values_list("user_id", flat=True)
            .distinct()
        )
        qs = (
            ReviewerProfile.objects.filter(user_id__in=user_ids)
            .select_related("user")
            .order_by("-total_upvotes_received")
        )
        paginator = CursorPagination()
        paginator.ordering = "-total_upvotes_received"
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ReviewerProfileSerializer(page, many=True).data
            )
        return success_response(ReviewerProfileSerializer(qs, many=True).data)
