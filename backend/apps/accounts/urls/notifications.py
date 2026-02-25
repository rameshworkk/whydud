"""Notification URL patterns for /api/v1/notifications/."""
from django.urls import path

from apps.accounts import notification_views as views

urlpatterns = [
    # GET /notifications — paginated list
    path("notifications", views.NotificationListView.as_view(), name="notification-list"),

    # GET /notifications/unread-count
    path("notifications/unread-count", views.UnreadCountView.as_view(), name="notification-unread-count"),

    # POST /notifications/mark-all-read
    path("notifications/mark-all-read", views.MarkAllReadView.as_view(), name="notification-mark-all-read"),

    # GET + PATCH /notifications/preferences
    path("notifications/preferences", views.PreferencesView.as_view(), name="notification-preferences"),

    # PATCH /notifications/:id/read
    path("notifications/<int:pk>/read", views.MarkReadView.as_view(), name="notification-mark-read"),

    # DELETE /notifications/:id
    path("notifications/<int:pk>", views.DismissView.as_view(), name="notification-dismiss"),
]
