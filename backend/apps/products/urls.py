"""URL patterns for the products app."""
from django.urls import path

from . import views

urlpatterns = [
    # Product catalogue
    path("products/lookup/", views.ProductLookupView.as_view(), name="product-lookup"),
    path("products/", views.ProductListView.as_view(), name="product-list"),
    path("products/<slug:slug>/", views.ProductDetailView.as_view(), name="product-detail"),
    path("products/<slug:slug>/price-history/", views.ProductPriceHistoryView.as_view(), name="product-price-history"),
    path("products/<slug:slug>/best-deals/", views.ProductBestDealsView.as_view(), name="product-best-deals"),
    path("products/<slug:slug>/tco/", views.ProductTCOView.as_view(), name="product-tco"),
    path("products/<slug:slug>/discussions/", views.ProductDiscussionsView.as_view(), name="product-discussions"),

    # Cross-platform price comparison
    path("products/<slug:slug>/listings/", views.ProductListingsView.as_view(), name="product-listings"),
    path("products/<slug:slug>/best-price/", views.BestPriceView.as_view(), name="product-best-price"),

    # Similar & alternatives
    path("products/<slug:slug>/similar/", views.SimilarProductsView.as_view(), name="product-similar"),
    path("products/<slug:slug>/alternatives/", views.AlternativeProductsView.as_view(), name="product-alternatives"),

    # Share
    path("products/<slug:slug>/share/", views.ShareProductView.as_view(), name="product-share"),

    # Comparison
    path("compare/share/", views.ShareCompareView.as_view(), name="compare-share"),
    path("compare/", views.CompareView.as_view(), name="compare"),

    # Bank card reference data (for card vault / payment optimizer)
    path("cards/banks/", views.BankListView.as_view(), name="banks-list"),
    path("cards/banks/<slug:bank_slug>/variants/", views.BankCardVariantsView.as_view(), name="bank-variants"),

    # Trending & Analytics
    path("trending/products", views.TrendingProductsView.as_view(), name="trending-products"),
    path("trending/rising", views.RisingProductsView.as_view(), name="trending-rising"),
    path("trending/price-dropping", views.PriceDroppingView.as_view(), name="trending-price-dropping"),
    path("categories/<slug:slug>/leaderboard", views.CategoryLeaderboardView.as_view(), name="category-leaderboard"),
    path("categories/<slug:slug>/most-loved", views.MostLovedView.as_view(), name="category-most-loved"),
    path("categories/<slug:slug>/most-hated", views.MostHatedView.as_view(), name="category-most-hated"),

    # Recently viewed (GET list + POST log)
    path("me/recently-viewed", views.RecentlyViewedView.as_view(), name="recently-viewed"),

    # Stock alerts (GET list + POST create, DELETE by id)
    path("alerts/stock", views.StockAlertListCreateView.as_view(), name="stock-alerts"),
    path("alerts/stock/<str:pk>", views.DeleteStockAlertView.as_view(), name="stock-alert-delete"),
]
