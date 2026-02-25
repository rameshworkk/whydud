import { apiClient } from "./client";
import type { PurchasePreference, PreferenceSchema } from "./types";

export const preferencesApi = {
  list: () =>
    apiClient.get<PurchasePreference[]>("/api/v1/preferences"),

  get: (categorySlug: string) =>
    apiClient.get<PurchasePreference>(`/api/v1/preferences/${categorySlug}`),

  save: (categorySlug: string, data: Record<string, unknown>) =>
    apiClient.post<PurchasePreference>(`/api/v1/preferences/${categorySlug}`, data),

  update: (categorySlug: string, data: Record<string, unknown>) =>
    apiClient.patch<PurchasePreference>(`/api/v1/preferences/${categorySlug}`, data),

  delete: (categorySlug: string) =>
    apiClient.delete(`/api/v1/preferences/${categorySlug}`),

  getSchema: (categorySlug: string) =>
    apiClient.get<PreferenceSchema>(`/api/v1/preferences/${categorySlug}/schema`),
};
