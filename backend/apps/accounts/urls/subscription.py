"""Subscription URL patterns for /api/v1/subscription/."""
from django.urls import path

from apps.accounts.subscription import (
    SubscriptionCancelView,
    SubscriptionCreateView,
    SubscriptionStatusView,
    SubscriptionVerifyView,
)

urlpatterns = [
    path("subscription/create", SubscriptionCreateView.as_view(), name="subscription-create"),
    path("subscription/verify", SubscriptionVerifyView.as_view(), name="subscription-verify"),
    path("subscription/cancel", SubscriptionCancelView.as_view(), name="subscription-cancel"),
    path("subscription/status", SubscriptionStatusView.as_view(), name="subscription-status"),
]
