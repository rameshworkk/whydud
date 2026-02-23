import { apiClient } from "./client";
import type { City, UserTCOProfile } from "@/types";

export interface TCOResult {
  purchasePrice: number;
  electricityCost: number;
  maintenanceCost: number;
  consumablesCost: number;
  totalCost: number;
  costPerYear: number;
  ownershipYears: number;
  breakdown: Array<{ label: string; amount: number }>;
}

export const tcoApi = {
  calculate: (productSlug: string, params: { cityId?: number; hoursPerDay?: number; years?: number }) =>
    apiClient.get<TCOResult>(`/api/v1/products/${productSlug}/tco`, { params }),

  compare: (slugs: string[], params: { cityId?: number; hoursPerDay?: number; years?: number }) =>
    apiClient.get<TCOResult[]>(`/api/v1/tco/compare`, {
      params: { slugs: slugs.join(","), ...params },
    }),

  getCities: () => apiClient.get<City[]>("/api/v1/tco/cities"),

  getProfile: () => apiClient.get<UserTCOProfile>("/api/v1/tco/profile"),

  updateProfile: (payload: Partial<Omit<UserTCOProfile, "id" | "city"> & { cityId: number }>) =>
    apiClient.patch<UserTCOProfile>("/api/v1/tco/profile", payload),
};
