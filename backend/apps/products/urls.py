"""URL patterns for the products app."""
from django.urls import path

from . import views

urlpatterns = [
    # Product catalogue
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<slug:slug>/price-history/", views.ProductPriceHistoryView.as_view(), name="product-price-history"),
    path("products/<slug:slug>/best-deals/", views.ProductBestDealsView.as_view(), name="product-best-deals"),
    path("products/<slug:slug>/tco/", views.ProductTCOView.as_view(), name="product-tco"),
    path("products/<slug:slug>/discussions/", views.ProductDiscussionsView.as_view(), name="product-discussions"),

    # Comparison
    path("compare/", views.CompareView.as_view(), name="compare"),

    # Bank card reference data (for card vault / payment optimizer)
    path("cards/banks/", views.BankListView.as_view(), name="banks-list"),
    path("cards/banks/<slug:bank_slug>/variants/", views.BankCardVariantsView.as_view(), name="bank-variants"),
]
