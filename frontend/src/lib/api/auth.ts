import { apiClient, clearToken } from "./client";
import type { User, WhydudEmail, PaymentMethod, MarketplacePreference } from "@/types";

export const authApi = {
  register: (payload: { email: string; password: string; name?: string; whydudUsername?: string }) =>
    apiClient.post<{ user: User; token: string }>("/api/v1/auth/register", payload),

  login: (payload: { email: string; password: string }) =>
    apiClient.post<{ user: User; token: string }>("/api/v1/auth/login", payload),

  logout: async () => {
    const res = await apiClient.post("/api/v1/auth/logout");
    clearToken();
    return res;
  },

  me: () => apiClient.get<User>("/api/v1/me"),

  deleteAccount: () => apiClient.delete("/api/v1/me"),

  changePassword: (payload: { currentPassword: string; newPassword: string }) =>
    apiClient.post<{ detail: string; token: string }>("/api/v1/auth/change-password", payload),

  forgotPassword: (payload: { email: string }) =>
    apiClient.post<{ detail: string }>("/api/v1/auth/forgot-password", payload),

  resetPassword: (payload: { uid: string; token: string; newPassword: string }) =>
    apiClient.post<{ detail: string }>("/api/v1/auth/reset-password", payload),

  verifyEmail: (payload: { uid: string; token: string }) =>
    apiClient.post<{ detail: string }>("/api/v1/auth/verify-email", payload),

  resendVerification: () =>
    apiClient.post<{ detail: string }>("/api/v1/auth/resend-verification"),

  exchangeOAuthCode: (code: string) =>
    apiClient.post<{ user: User; token: string }>("/api/v1/auth/oauth/exchange-code", { code }),
};

export const whydudEmailApi = {
  create: (username: string) =>
    apiClient.post<WhydudEmail>("/api/v1/email/whydud/create", { username }),

  checkAvailability: (username: string) =>
    apiClient.get<{ available: boolean }>("/api/v1/email/whydud/check-availability", {
      params: { username },
    }),

  getStatus: () => apiClient.get<WhydudEmail>("/api/v1/email/whydud/status"),
};

export const marketplacePreferencesApi = {
  get: () =>
    apiClient.get<MarketplacePreference>("/api/v1/me/marketplace-preferences"),

  update: (preferredMarketplaces: number[]) =>
    apiClient.put<MarketplacePreference>("/api/v1/me/marketplace-preferences", {
      preferredMarketplaces,
    }),
};

export const cardVaultApi = {
  list: () => apiClient.get<PaymentMethod[]>("/api/v1/cards"),

  add: (payload: Omit<PaymentMethod, "id" | "createdAt">) =>
    apiClient.post<PaymentMethod>("/api/v1/cards", payload),

  update: (id: string, payload: Partial<PaymentMethod>) =>
    apiClient.patch<PaymentMethod>(`/api/v1/cards/${id}`, payload),

  remove: (id: string) => apiClient.delete(`/api/v1/cards/${id}`),

  listBanks: () => apiClient.get<Array<{ slug: string; name: string }>>("/api/v1/cards/banks"),

  getBankVariants: (bankSlug: string) =>
    apiClient.get<Array<{ variant: string; type: string }>>(`/api/v1/cards/banks/${bankSlug}/variants`),
};
