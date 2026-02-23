/**
 * Base API client. All requests go through here.
 * Never use raw fetch in components — always use the typed wrappers in lib/api/*.
 */
import type { ApiResponse } from "@/types/api";

const API_BASE =
  typeof window === "undefined"
    ? // Server-side: call Django directly (internal network in Docker)
      (process.env.INTERNAL_API_URL ?? "http://backend:8000")
    : // Client-side: go through Next.js rewrites
      "";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { body, params, ...init } = options;

  const url = new URL(`${API_BASE}${path}`);
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(k, String(v));
    });
  }

  try {
    const response = await fetch(url.toString(), {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(init.headers ?? {}),
      },
      credentials: "include", // send session cookie
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const json = (await response.json()) as ApiResponse<T>;
    return json;
  } catch {
    return { success: false, error: { code: "NETWORK_ERROR", message: "Network request failed" } } as ApiResponse<T>;
  }
}

export const apiClient = {
  get: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "GET" }),

  post: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "POST", body }),

  patch: <T>(path: string, body?: unknown, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "PATCH", body }),

  delete: <T>(path: string, opts?: RequestOptions) =>
    request<T>(path, { ...opts, method: "DELETE" }),
};
