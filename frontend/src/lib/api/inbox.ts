import { apiClient } from "./client";
import type { InboxEmail, PaginatedResponse, ParsedOrder } from "@/types";

export interface InboxFilters {
  [key: string]: string | boolean | undefined;
  category?: string;
  isRead?: boolean;
  isStarred?: boolean;
  cursor?: string;
}

export const inboxApi = {
  list: (filters?: InboxFilters) =>
    apiClient.get<PaginatedResponse<InboxEmail>>("/api/v1/inbox", { params: filters }),

  get: (id: string) => apiClient.get<InboxEmail & { bodyHtml?: string }>(`/api/v1/inbox/${id}`),

  markRead: (id: string, isRead: boolean) =>
    apiClient.patch(`/api/v1/inbox/${id}`, { isRead }),

  star: (id: string, isStarred: boolean) =>
    apiClient.patch(`/api/v1/inbox/${id}`, { isStarred }),

  softDelete: (id: string) => apiClient.delete(`/api/v1/inbox/${id}`),

  reparse: (id: string) => apiClient.post(`/api/v1/inbox/${id}/reparse`),
};

export const purchasesApi = {
  list: (cursor?: string) =>
    apiClient.get<PaginatedResponse<ParsedOrder>>("/api/v1/purchases", { params: { cursor } }),

  getDashboard: () =>
    apiClient.get<Record<string, unknown>>("/api/v1/purchases/dashboard"),

  getRefunds: () =>
    apiClient.get<Record<string, unknown>[]>("/api/v1/purchases/refunds"),

  getReturnWindows: () =>
    apiClient.get<Record<string, unknown>[]>("/api/v1/purchases/return-windows"),

  getSubscriptions: () =>
    apiClient.get<Record<string, unknown>[]>("/api/v1/purchases/subscriptions"),
};
