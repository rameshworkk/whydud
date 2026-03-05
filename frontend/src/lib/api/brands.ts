import { apiClient } from "./client";
import type { BrandLeaderboard, BrandTrustScore, ProductSummary } from "@/types";

export const brandsApi = {
  /** GET /api/v1/brands/{slug}/trust-score */
  getTrustScore: (slug: string) =>
    apiClient.get<BrandTrustScore>(`/api/v1/brands/${slug}/trust-score`),

  /** GET /api/v1/brands/leaderboard — top/bottom 20 brands by trust score */
  getLeaderboard: () =>
    apiClient.get<BrandLeaderboard>("/api/v1/brands/leaderboard"),

  /** GET /api/v1/products?brand={slug} — products for a brand */
  getProducts: (brandSlug: string, cursor?: string) =>
    apiClient.get<ProductSummary[]>("/api/v1/products", {
      params: { brand: brandSlug, cursor },
    }),
};
