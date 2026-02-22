import { apiClient } from "./client";
import type { PaginatedResponse, ProductSummary } from "@/types";

export interface SearchFilters {
  category?: string;
  brand?: string;
  minPrice?: number;
  maxPrice?: number;
  minDudScore?: number;
  inStock?: boolean;
  sortBy?: "relevance" | "dudscore" | "price_asc" | "price_desc" | "newest";
  cursor?: string;
}

export const searchApi = {
  search: (query: string, filters?: SearchFilters) =>
    apiClient.get<PaginatedResponse<ProductSummary>>("/api/v1/search", {
      params: { q: query, ...filters },
    }),

  autocomplete: (query: string) =>
    apiClient.get<Array<{ id: string; title: string; slug: string; categoryName: string }>>(
      "/api/v1/search/autocomplete",
      { params: { q: query } }
    ),

  triggerAdhocScrape: (url: string) =>
    apiClient.post<{ jobId: string }>("/api/v1/search/adhoc", { url }),
};
