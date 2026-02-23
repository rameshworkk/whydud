from django.urls import path
from . import views

urlpatterns = [
    path("wishlists", views.WishlistListCreateView.as_view(), name="wishlists-list"),
    path("wishlists/shared/<str:slug>", views.SharedWishlistView.as_view(), name="wishlists-shared"),
    path("wishlists/<str:pk>", views.WishlistDetailView.as_view(), name="wishlists-detail"),
    path("wishlists/<str:pk>/items", views.WishlistItemCreateView.as_view(), name="wishlist-items-create"),
    path("wishlists/<str:pk>/items/<str:product_id>", views.WishlistItemDetailView.as_view(), name="wishlist-item-detail"),
]
