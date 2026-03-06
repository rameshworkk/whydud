import { apiClient } from "./client";
import type {
  Category,
  Deal,
  Department,
  DiscussionThread,
  MarketplaceOffer,
  ProductDetail,
  ProductSummary,
  PricePoint,
  Review,
  ShareData,
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

  getReviews: (
    slug: string,
    params?: { cursor?: string; sort?: string; source?: string; rating?: string; verified?: string },
  ) =>
    apiClient.get<Review[]>(`/api/v1/products/${slug}/reviews`, {
      params,
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

  getShareData: (slug: string) =>
    apiClient.get<ShareData>(`/api/v1/products/${slug}/share`),

  compare: (slugs: string[]) =>
    apiClient.get<{ products: ProductDetail[]; priceMatrix: Record<string, unknown>[]; specDiff: Record<string, unknown> }>(`/api/v1/compare`, {
      params: { slugs: slugs.join(",") },
    }),

  /** Lookup a product by marketplace slug + external ID (URL prefix feature) */
  lookup: (marketplace: string, externalId: string) =>
    apiClient.get<{ slug: string; title: string; marketplace: string; externalId: string }>(
      "/api/v1/products/lookup",
      { params: { marketplace, external_id: externalId } },
    ),
};

export const clicksApi = {
  /** POST /api/v1/clicks/track — log click, return affiliate redirect URL */
  track: (listingId: string, referrerPage: string, sourceSection?: string) =>
    apiClient.post<{ affiliateUrl: string; clickId: number }>(
      "/api/v1/clicks/track",
      { listingId, referrerPage, sourceSection },
    ),
};

export const recentlyViewedApi = {
  /** POST /api/v1/me/recently-viewed — log a product view (auth required) */
  log: (productSlug: string) =>
    apiClient.post<void>("/api/v1/me/recently-viewed", { productSlug }),

  /** GET /api/v1/me/recently-viewed — list recently viewed products (auth required) */
  list: (limit = 8) =>
    apiClient.get<ProductSummary[]>("/api/v1/me/recently-viewed", {
      params: { limit },
    }),
};

export const categoriesApi = {
  /** GET /api/v1/categories/tree/ — full 3-level department > category > subcategory tree */
  getTree: () =>
    apiClient.get<Department[]>("/api/v1/categories/tree/"),

  /** GET /api/v1/categories/ — flat list with optional level/parent filters */
  list: (params?: { level?: number; parent?: string }) =>
    apiClient.get<Category[]>("/api/v1/categories/", { params }),

  /** GET /api/v1/categories/:slug/ — single category detail */
  getDetail: (slug: string) =>
    apiClient.get<Category>(`/api/v1/categories/${slug}/`),
};

export const dealsApi = {
  /** Returns Deal[] in .data (paginated) */
  list: (params?: { dealType?: string; cursor?: string }) =>
    apiClient.get<Deal[]>(`/api/v1/deals`, { params }),

  get: (id: string) => apiClient.get<Deal>(`/api/v1/deals/${id}`),

  trackClick: (id: string) => apiClient.post(`/api/v1/deals/${id}/click`),
};
