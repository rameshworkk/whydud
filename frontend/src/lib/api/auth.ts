import { apiClient } from "./client";
import type { User, WhydudEmail, PaymentMethod } from "@/types";

export const authApi = {
  register: (payload: { email: string; password: string; name?: string; whydudUsername?: string }) =>
    apiClient.post<{ user: User; token?: string }>("/api/v1/auth/register", payload),

  login: (payload: { email: string; password: string }) =>
    apiClient.post<{ user: User }>("/api/v1/auth/login", payload),

  logout: () => apiClient.post("/api/v1/auth/logout"),

  me: () => apiClient.get<User>("/api/v1/me"),

  deleteAccount: () => apiClient.delete("/api/v1/me"),
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
