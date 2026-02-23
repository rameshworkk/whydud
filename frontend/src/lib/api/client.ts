/**
 * Base API client. All requests go through here.
 * Never use raw fetch in components — always use the typed wrappers in lib/api/*.
 */
import type { ApiResponse } from "@/types/api";

const API_BASE =
  typeof window === "undefined"
    ? // Server-side: call Django directly (internal network in Docker)
      (process.env.INTERNAL_API_URL ?? "http://localhost:8000")
    : // Client-side: go through Next.js rewrites
      "";

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
  params?: Record<string, string | number | boolean | undefined>;
}

/** Convert a single snake_case string to camelCase */
function toCamelCase(str: string): string {
  return str.replace(/_([a-z0-9])/g, (_, c) => c.toUpperCase());
}

/** Recursively convert all object keys from snake_case to camelCase */
function snakeToCamel(obj: unknown): unknown {
  if (obj === null || obj === undefined || typeof obj !== "object") {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(snakeToCamel);
  }
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    result[toCamelCase(key)] = snakeToCamel(value);
  }
  return result;
}

/** Convert a single camelCase string to snake_case */
function toSnakeCase(str: string): string {
  return str.replace(/[A-Z]/g, (c) => `_${c.toLowerCase()}`);
}

/** Recursively convert all object keys from camelCase to snake_case (for request bodies) */
function camelToSnake(obj: unknown): unknown {
  if (obj === null || obj === undefined || typeof obj !== "object") {
    return obj;
  }
  if (Array.isArray(obj)) {
    return obj.map(camelToSnake);
  }
  const result: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(obj as Record<string, unknown>)) {
    result[toSnakeCase(key)] = camelToSnake(value);
  }
  return result;
}

async function request<T>(
  path: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> {
  const { body, params, ...init } = options;

  // Convert query param keys to snake_case for Django
  const url = new URL(`${API_BASE}${path}`, API_BASE || "http://localhost:3000");
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined) url.searchParams.set(toSnakeCase(k), String(v));
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
      body: body !== undefined ? JSON.stringify(camelToSnake(body)) : undefined,
    });

    const raw = await response.json();
    const json = snakeToCamel(raw) as ApiResponse<T>;
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
