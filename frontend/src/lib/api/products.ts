import { apiClient } from "./client";
import type {
  Deal,
  DiscussionThread,
  MarketplaceOffer,
  ProductDetail,
  ProductSummary,
  PricePoint,
  Review,
} from "@/types";

export const productsApi = {
  /** Returns ProductSummary[] in .data (paginated, cursor in pagination.next) */
  list: (params?: { category?: string; brand?: string; cursor?: string }) =>
    apiClient.get<ProductSummary[]>("/api/v1/products", { params }),

  getDetail: (slug: string) =>
    apiClient.get<ProductDetail>(`/api/v1/products/${slug}`),

  getPriceHistory: (slug: string, days = 90) =>
    apiClient.get<PricePoint[]>(`/api/v1/products/${slug}/price-history`, {
      params: { days },
    }),

  getReviews: (slug: string, cursor?: string) =>
    apiClient.get<Review[]>(`/api/v1/products/${slug}/reviews`, {
      params: { cursor },
    }),

  getBestDeals: (slug: string) =>
    apiClient.get<MarketplaceOffer[]>(`/api/v1/products/${slug}/best-deals`),

  getTco: (slug: string, params: { cityId?: number; hoursPerDay?: number }) =>
    apiClient.get<Record<string, unknown>>(`/api/v1/products/${slug}/tco`, { params }),

  getDiscussions: (slug: string, cursor?: string) =>
    apiClient.get<DiscussionThread[]>(`/api/v1/products/${slug}/discussions`, {
      params: { cursor },
    }),

  getSimilar: (slug: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/products/${slug}/similar`),

  getAlternatives: (slug: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/products/${slug}/alternatives`),

  compare: (slugs: string[]) =>
    apiClient.get<ProductDetail[]>(`/api/v1/compare`, {
      params: { slugs: slugs.join(",") },
    }),
};

export const clicksApi = {
  /** POST /api/v1/clicks/track — log click, return affiliate redirect URL */
  track: (listingId: string, referrerPage: string, sourceSection?: string) =>
    apiClient.post<{ affiliateUrl: string; clickId: number }>(
      "/api/v1/clicks/track",
      { listingId, referrerPage, sourceSection },
    ),
};

export const dealsApi = {
  /** Returns Deal[] in .data (paginated) */
  list: (params?: { dealType?: string; cursor?: string }) =>
    apiClient.get<Deal[]>(`/api/v1/deals`, { params }),

  get: (id: string) => apiClient.get<Deal>(`/api/v1/deals/${id}`),

  trackClick: (id: string) => apiClient.post(`/api/v1/deals/${id}/click`),
};
