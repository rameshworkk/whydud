import { apiClient } from "./client";
import type { Deal, MarketplaceOffer, PaginatedResponse, ProductDetail, ProductSummary, PricePoint, Review } from "@/types";

export const productsApi = {
  getDetail: (slug: string) =>
    apiClient.get<ProductDetail>(`/api/v1/products/${slug}`),

  getPriceHistory: (slug: string, days = 90) =>
    apiClient.get<PricePoint[]>(`/api/v1/products/${slug}/price-history`, {
      params: { days },
    }),

  getReviews: (slug: string, cursor?: string) =>
    apiClient.get<PaginatedResponse<Review>>(`/api/v1/products/${slug}/reviews`, {
      params: { cursor },
    }),

  getBestDeals: (slug: string) =>
    apiClient.get<MarketplaceOffer[]>(`/api/v1/products/${slug}/best-deals`),

  getTco: (slug: string, params: { cityId?: number; hoursPerDay?: number }) =>
    apiClient.get<Record<string, unknown>>(`/api/v1/products/${slug}/tco`, { params }),

  getDiscussions: (slug: string, cursor?: string) =>
    apiClient.get<PaginatedResponse<Record<string, unknown>>>(`/api/v1/products/${slug}/discussions`, {
      params: { cursor },
    }),

  compare: (slugs: string[]) =>
    apiClient.get<ProductDetail[]>(`/api/v1/compare`, {
      params: { slugs: slugs.join(",") },
    }),
};

export const dealsApi = {
  list: (params?: { dealType?: string; cursor?: string }) =>
    apiClient.get<PaginatedResponse<Deal>>(`/api/v1/deals`, { params }),

  get: (id: string) => apiClient.get<Deal>(`/api/v1/deals/${id}`),

  trackClick: (id: string) => apiClient.post(`/api/v1/deals/${id}/click`),
};
