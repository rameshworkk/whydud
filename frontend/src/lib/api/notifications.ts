import { apiClient } from "./client";
import type { Notification, NotificationPreferences } from "./types";

export const notificationsApi = {
  list: (cursor?: string) =>
    apiClient.get<Notification[]>("/api/v1/notifications", {
      params: cursor ? { cursor } : undefined,
    }),

  getUnreadCount: () =>
    apiClient.get<{ count: number }>("/api/v1/notifications/unread-count"),

  markAsRead: (id: number) =>
    apiClient.patch(`/api/v1/notifications/${id}/read`),

  markAllAsRead: () =>
    apiClient.post("/api/v1/notifications/mark-all-read"),

  dismiss: (id: number) =>
    apiClient.delete(`/api/v1/notifications/${id}`),

  getPreferences: () =>
    apiClient.get<NotificationPreferences>("/api/v1/notifications/preferences"),

  updatePreferences: (prefs: Partial<NotificationPreferences>) =>
    apiClient.patch<NotificationPreferences>("/api/v1/notifications/preferences", prefs),
};
