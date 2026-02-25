import { apiClient } from "./client";
import type { ProductSummary } from "@/types";

export const trendingApi = {
  getTrendingProducts: () =>
    apiClient.get<ProductSummary[]>("/api/v1/trending/products"),

  getRisingProducts: () =>
    apiClient.get<ProductSummary[]>("/api/v1/trending/rising"),

  getPriceDropping: () =>
    apiClient.get<ProductSummary[]>("/api/v1/trending/price-dropping"),

  getCategoryLeaderboard: (slug: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/categories/${slug}/leaderboard`),

  getMostLoved: (slug: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/categories/${slug}/most-loved`),

  getMostHated: (slug: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/categories/${slug}/most-hated`),
};
