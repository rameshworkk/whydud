import { apiClient } from "./client";
import type { PriceAlert } from "@/types";
import type { StockAlert } from "./types";

export const alertsApi = {
  createPriceAlert: (productId: string, targetPrice: number, marketplace?: string) =>
    apiClient.post<PriceAlert>("/api/v1/alerts/price", {
      product: productId,
      targetPrice,
      ...(marketplace && { marketplace }),
    }),

  getAlerts: () =>
    apiClient.get<PriceAlert[]>("/api/v1/alerts"),

  updateAlert: (id: string, targetPrice: number) =>
    apiClient.patch<PriceAlert>(`/api/v1/alerts/${id}`, { targetPrice }),

  deleteAlert: (id: string) =>
    apiClient.delete(`/api/v1/alerts/${id}`),

  getTriggeredAlerts: () =>
    apiClient.get<PriceAlert[]>("/api/v1/alerts/triggered"),

  createStockAlert: (productId: string, listingId: string) =>
    apiClient.post<StockAlert>("/api/v1/alerts/stock", {
      product: productId,
      listing: listingId,
    }),

  getStockAlerts: () =>
    apiClient.get<StockAlert[]>("/api/v1/alerts/stock"),

  deleteStockAlert: (id: string) =>
    apiClient.delete(`/api/v1/alerts/stock/${id}`),
};
