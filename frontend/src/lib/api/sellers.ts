import { apiClient } from "./client";
import type { SellerDetail, ProductSummary, Review } from "@/types";

export const sellersApi = {
  getDetail: (slug: string) =>
    apiClient.get<SellerDetail>(`/api/v1/sellers/${slug}`),

  getProducts: (slug: string, cursor?: string) =>
    apiClient.get<ProductSummary[]>(`/api/v1/sellers/${slug}/products`, {
      params: { cursor },
    }),

  getReviews: (slug: string, cursor?: string) =>
    apiClient.get<Review[]>(`/api/v1/sellers/${slug}/reviews`, {
      params: { cursor },
    }),
};
