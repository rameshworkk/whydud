import { apiClient } from "./client";
import type { GiftCard, GiftCardRedemption, RewardBalance, RewardPointsLedger } from "@/types";

export const rewardsApi = {
  getBalance: () => apiClient.get<RewardBalance>("/api/v1/rewards/balance"),

  getHistory: (cursor?: string) =>
    apiClient.get<RewardPointsLedger[]>("/api/v1/rewards/history", { params: { cursor } }),

  getGiftCards: () => apiClient.get<GiftCard[]>("/api/v1/rewards/gift-cards"),

  redeem: (catalogId: number, denomination: number, deliveryEmail?: string) =>
    apiClient.post("/api/v1/rewards/redeem", { catalogId, denomination, deliveryEmail }),

  getRedemptions: () => apiClient.get<GiftCardRedemption[]>("/api/v1/rewards/redemptions"),
};
