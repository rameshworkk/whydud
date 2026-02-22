import { apiClient } from "./client";
import type { Wishlist } from "@/types";

export const wishlistsApi = {
  list: () => apiClient.get<Wishlist[]>("/api/v1/wishlists"),

  create: (name: string) => apiClient.post<Wishlist>("/api/v1/wishlists", { name }),

  update: (id: string, payload: { name?: string; isPublic?: boolean }) =>
    apiClient.patch<Wishlist>(`/api/v1/wishlists/${id}`, payload),

  delete: (id: string) => apiClient.delete(`/api/v1/wishlists/${id}`),

  addItem: (wishlistId: string, productId: string, targetPrice?: number) =>
    apiClient.post(`/api/v1/wishlists/${wishlistId}/items`, { product: productId, targetPrice }),

  removeItem: (wishlistId: string, productId: string) =>
    apiClient.delete(`/api/v1/wishlists/${wishlistId}/items/${productId}`),

  updateItem: (wishlistId: string, productId: string, payload: { targetPrice?: number; notes?: string; alertEnabled?: boolean }) =>
    apiClient.patch(`/api/v1/wishlists/${wishlistId}/items/${productId}`, payload),

  getShared: (slug: string) => apiClient.get<Wishlist>(`/api/v1/wishlists/shared/${slug}`),
};
