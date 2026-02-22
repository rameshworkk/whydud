"""Shared DRF permission classes."""
from rest_framework.permissions import BasePermission


class IsConnectedUser(BasePermission):
    """Allows access only to users with an active @whyd.xyz email or Gmail link."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "has_whydud_email", False)
        )


class IsPremiumUser(BasePermission):
    """Allows access only to premium subscribers."""

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "subscription_tier", "free") == "premium"
        )
