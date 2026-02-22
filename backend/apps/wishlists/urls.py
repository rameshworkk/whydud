from django.urls import path
from . import views

urlpatterns = [
    path("wishlists", views.WishlistListCreateView.as_view(), name="wishlists-list"),
    path("wishlists/<uuid:pk>", views.WishlistDetailView.as_view(), name="wishlists-detail"),
    path("wishlists/<uuid:pk>/items", views.WishlistItemView.as_view(), name="wishlists-items"),
    path("wishlists/<uuid:pk>/items/<uuid:product_id>", views.WishlistItemView.as_view(), name="wishlists-item-detail"),
    path("wishlists/shared/<slug:slug>", views.PublicWishlistView.as_view(), name="wishlists-shared"),
]
