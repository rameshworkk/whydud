"""Wishlist views."""
import uuid

from django.shortcuts import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from common.utils import error_response, success_response

from .models import Wishlist, WishlistItem
from .serializers import WishlistDetailSerializer, WishlistItemSerializer, WishlistSerializer


class WishlistListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        wishlists = Wishlist.objects.filter(user=request.user).order_by("-is_default", "name")
        return success_response(WishlistSerializer(wishlists, many=True).data)

    def post(self, request: Request) -> Response:
        serializer = WishlistSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))

        # Only one default per user
        is_default = request.data.get("is_default", False)
        if is_default:
            Wishlist.objects.filter(user=request.user, is_default=True).update(is_default=False)

        wishlist = serializer.save(user=request.user)
        return success_response(WishlistSerializer(wishlist).data, status=201)


class WishlistDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: str) -> Response:
        wishlist = get_object_or_404(Wishlist, pk=pk, user=request.user)
        return success_response(WishlistDetailSerializer(wishlist).data)

    def patch(self, request: Request, pk: str) -> Response:
        wishlist = get_object_or_404(Wishlist, pk=pk, user=request.user)
        serializer = WishlistSerializer(wishlist, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, pk: str) -> Response:
        wishlist = get_object_or_404(Wishlist, pk=pk, user=request.user)
        if wishlist.is_default:
            return error_response("cannot_delete_default", "Cannot delete your default wishlist.")
        wishlist.delete()
        return success_response({"detail": "Wishlist deleted."})


class WishlistItemCreateView(APIView):
    """POST /api/v1/wishlists/:pk/items — add a product to a wishlist."""
    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: str) -> Response:
        from apps.products.models import Product

        wishlist = get_object_or_404(Wishlist, pk=pk, user=request.user)

        product_id = request.data.get("product_id")
        if not product_id:
            return error_response("validation_error", "product_id is required.")

        try:
            product = Product.objects.get(pk=product_id)
        except (Product.DoesNotExist, ValueError):
            return error_response("not_found", "Product not found.", status=404)

        if WishlistItem.objects.filter(wishlist=wishlist, product=product).exists():
            return error_response("already_in_wishlist", "Product already in this wishlist.")

        item = WishlistItem.objects.create(
            wishlist=wishlist,
            product=product,
            price_when_added=product.current_best_price,
            target_price=request.data.get("target_price"),
            notes=request.data.get("notes", ""),
            priority=request.data.get("priority", 0),
        )
        return success_response(WishlistItemSerializer(item).data, status=201)


class WishlistItemDetailView(APIView):
    """PATCH/DELETE /api/v1/wishlists/:pk/items/:product_id"""
    permission_classes = [IsAuthenticated]

    def _get_item(self, pk: str, product_id: str, user) -> WishlistItem | None:
        return WishlistItem.objects.filter(
            wishlist__pk=pk, wishlist__user=user, product__pk=product_id
        ).first()

    def patch(self, request: Request, pk: str, product_id: str) -> Response:
        item = self._get_item(pk, product_id, request.user)
        if not item:
            return error_response("not_found", "Wishlist item not found.", status=404)
        serializer = WishlistItemSerializer(item, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_response("validation_error", str(serializer.errors))
        serializer.save()
        return success_response(serializer.data)

    def delete(self, request: Request, pk: str, product_id: str) -> Response:
        item = self._get_item(pk, product_id, request.user)
        if not item:
            return error_response("not_found", "Wishlist item not found.", status=404)
        item.delete()
        return success_response({"detail": "Item removed."})


class SharedWishlistView(APIView):
    """GET /api/v1/wishlists/shared/:slug — public wishlist by share slug."""
    permission_classes = [AllowAny]

    def get(self, request: Request, slug: str) -> Response:
        wishlist = Wishlist.objects.filter(share_slug=slug, is_public=True).first()
        if not wishlist:
            return error_response("not_found", "Wishlist not found.", status=404)
        return success_response(WishlistDetailSerializer(wishlist).data)
