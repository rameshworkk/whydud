"""Review views."""
from django.db import transaction
from django.db.models import F
from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.pagination import CursorPagination
from common.utils import error_response, success_response

from .models import Review, ReviewVote
from .serializers import ReviewSerializer, ReviewVoteSerializer


class ProductReviewsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        from apps.products.models import Product

        product = get_object_or_404(Product, slug=slug)
        sort = request.query_params.get("sort", "helpful")
        rating = request.query_params.get("rating")
        verified_only = request.query_params.get("verified") == "1"

        qs = Review.objects.filter(product=product, is_flagged=False).select_related(
            "listing__marketplace"
        )

        if rating:
            try:
                qs = qs.filter(rating=int(rating))
            except ValueError:
                pass
        if verified_only:
            qs = qs.filter(is_verified_purchase=True)

        sort_map = {
            "helpful": "-vote_score",
            "recent": "-review_date",
            "rating_asc": "rating",
            "rating_desc": "-rating",
        }
        qs = qs.order_by(sort_map.get(sort, "-vote_score"))

        paginator = CursorPagination()
        page = paginator.paginate_queryset(qs, request)
        if page is not None:
            return paginator.get_paginated_response(
                ReviewSerializer(page, many=True, context={"request": request}).data
            )
        return success_response(ReviewSerializer(qs, many=True, context={"request": request}).data)


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
