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

/**
 * Coerce string values that look like numbers into actual numbers.
 * Django/DRF serializes Decimal fields as strings (e.g. "3.92", "2999900.00").
 * Frontend code expects numbers for .toFixed(), arithmetic, comparisons, etc.
 */
function coerceNumericString(value: unknown): unknown {
  if (typeof value !== "string") return value;
  // Skip empty strings, UUIDs, dates, URLs, and other non-numeric strings
  if (value === "" || value.includes("-") && value.length > 10) return value;
  if (value.includes("/") || value.includes("@") || value.includes(" ")) return value;
  // Match strings that are purely numeric (with optional decimal point)
  if (/^\d+(\.\d+)?$/.test(value)) {
    const n = Number(value);
    if (!isNaN(n) && isFinite(n)) return n;
  }
  return value;
}

/** Recursively convert all object keys from snake_case to camelCase */
function snakeToCamel(obj: unknown): unknown {
  if (obj === null || obj === undefined || typeof obj !== "object") {
    return coerceNumericString(obj);
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

// ── Token helpers (DRF TokenAuthentication) ──
const TOKEN_KEY = "whydud_auth_token";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  if (typeof window !== "undefined") {
    localStorage.setItem(TOKEN_KEY, token);
    // Set a cookie flag so Next.js middleware can detect auth (not the actual token)
    document.cookie = "whydud_auth=1; path=/; max-age=31536000; SameSite=Lax";
  }
}

export function clearToken(): void {
  if (typeof window !== "undefined") {
    localStorage.removeItem(TOKEN_KEY);
    document.cookie = "whydud_auth=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  }
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

  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (token) {
    headers["Authorization"] = `Token ${token}`;
  }

  try {
    const response = await fetch(url.toString(), {
      ...init,
      headers,
      credentials: "include",
      body: body !== undefined ? JSON.stringify(camelToSnake(body)) : undefined,
    });

    const raw = await response.json();
    const json = snakeToCamel(raw) as Record<string, unknown>;

    // Handle DRF's standard error responses that don't use our { success, data } envelope
    // e.g. { detail: "Authentication credentials were not provided." }
    if (!response.ok && !("success" in raw)) {
      const message =
        typeof json.detail === "string"
          ? json.detail
          : typeof raw.detail === "string"
            ? raw.detail
            : response.statusText || "Request failed";
      const code =
        response.status === 401 || response.status === 403
          ? "NOT_AUTHENTICATED"
          : `HTTP_${response.status}`;
      return { success: false, error: { code, message } } as ApiResponse<T>;
    }

    return json as unknown as ApiResponse<T>;
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
