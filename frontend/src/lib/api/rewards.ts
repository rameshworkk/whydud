import { apiClient } from "./client";
import type { RewardBalance } from "@/types";

export interface GiftCard {
  id: number;
  brandName: string;
  brandSlug: string;
  brandLogoUrl: string;
  denominations: number[];
  category: string;
}

export const rewardsApi = {
  getBalance: () => apiClient.get<RewardBalance>("/api/v1/rewards/balance"),

  getHistory: (cursor?: string) =>
    apiClient.get<Record<string, unknown>[]>("/api/v1/rewards/history", { params: { cursor } }),

  getGiftCards: () => apiClient.get<GiftCard[]>("/api/v1/rewards/gift-cards"),

  redeem: (catalogId: number, denomination: number, deliveryEmail?: string) =>
    apiClient.post("/api/v1/rewards/redeem", { catalogId, denomination, deliveryEmail }),

  getRedemptions: () => apiClient.get<Record<string, unknown>[]>("/api/v1/rewards/redemptions"),
};
