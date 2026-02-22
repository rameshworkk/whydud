from django.urls import path
from . import views

urlpatterns = [
    path("inbox", views.InboxListView.as_view(), name="inbox-list"),
    path("inbox/<uuid:pk>", views.InboxDetailView.as_view(), name="inbox-detail"),
    path("inbox/<uuid:pk>/reparse", views.InboxReparseView.as_view(), name="inbox-reparse"),
    path("purchases", views.PurchaseListView.as_view(), name="purchases-list"),
    path("purchases/dashboard", views.PurchaseDashboardView.as_view(), name="purchases-dashboard"),
    path("purchases/refunds", views.RefundsView.as_view(), name="purchases-refunds"),
    path("purchases/return-windows", views.ReturnWindowsView.as_view(), name="purchases-return-windows"),
    path("purchases/subscriptions", views.SubscriptionsView.as_view(), name="purchases-subscriptions"),
]
