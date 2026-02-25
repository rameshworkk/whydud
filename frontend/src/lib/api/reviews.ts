import { apiClient } from "./client";
import type { Review } from "@/types";
import type { WriteReviewPayload, ReviewFeature, ReviewerProfile } from "./types";

export const reviewsApi = {
  submit: (slug: string, payload: WriteReviewPayload) =>
    apiClient.post<Review>(`/api/v1/products/${slug}/reviews`, payload),

  edit: (id: string, payload: Partial<WriteReviewPayload>) =>
    apiClient.patch<Review>(`/api/v1/reviews/${id}`, payload),

  delete: (id: string) =>
    apiClient.delete(`/api/v1/reviews/${id}`),

  getMyReviews: () =>
    apiClient.get<Review[]>("/api/v1/me/reviews"),

  getFeatures: (slug: string) =>
    apiClient.get<ReviewFeature[]>(`/api/v1/products/${slug}/review-features`),

  uploadPurchaseProof: async (reviewId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);

    const { getToken } = await import("./client");
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) headers["Authorization"] = `Token ${token}`;

    const res = await fetch(`/api/v1/reviews/${reviewId}/purchase-proof`, {
      method: "POST",
      headers,
      credentials: "include",
      body: formData,
    });
    return res.json();
  },

  getReviewerProfile: () =>
    apiClient.get<ReviewerProfile>("/api/v1/me/reviewer-profile"),

  getLeaderboard: (cursor?: string) =>
    apiClient.get<ReviewerProfile[]>("/api/v1/leaderboard/reviewers", {
      params: cursor ? { cursor } : undefined,
    }),

  getCategoryLeaderboard: (categorySlug: string, cursor?: string) =>
    apiClient.get<ReviewerProfile[]>(
      `/api/v1/leaderboard/reviewers/${categorySlug}`,
      { params: cursor ? { cursor } : undefined },
    ),
};
