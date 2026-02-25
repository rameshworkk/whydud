import { apiClient } from "./client";
import type { City, UserTCOProfile } from "@/types";
import type { TCOModelSchema, TCOResult } from "./types";

export interface TCOCalculatePayload {
  productSlug: string;
  ownershipYears?: number;
  cityId?: number;
  electricityTariff?: number;
  inputs?: Record<string, number>;
}

export interface TCOCompareResult {
  product: { slug: string; title: string; brand: string | null; currentBestPrice: number | null; image: string | null };
  tco: TCOResult;
}

export const tcoApi = {
  getModel: (categorySlug: string) =>
    apiClient.get<TCOModelSchema>(`/api/v1/tco/models/${categorySlug}`),

  calculateTCO: (payload: TCOCalculatePayload) =>
    apiClient.post<TCOResult>("/api/v1/tco/calculate", payload),

  compareTCO: (productSlugs: string[], params?: { ownershipYears?: number; cityId?: number; electricityTariff?: number }) =>
    apiClient.get<{ comparisons: TCOCompareResult[] }>("/api/v1/tco/compare", {
      params: { products: productSlugs.join(","), ...params },
    }),

  getCities: () => apiClient.get<City[]>("/api/v1/tco/cities"),

  getProfile: () => apiClient.get<UserTCOProfile>("/api/v1/tco/profile"),

  updateProfile: (payload: Partial<Omit<UserTCOProfile, "id" | "city"> & { cityId: number }>) =>
    apiClient.patch<UserTCOProfile>("/api/v1/tco/profile", payload),
};
