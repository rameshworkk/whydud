/** Standard API response envelopes from Django backend. */

export interface ApiSuccess<T> {
  success: true;
  data: T;
}

export interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResponse<T> = ApiSuccess<T> | ApiError;

/**
 * Paginated responses from the backend have this shape at the TOP level:
 *   { success: true, data: T[], pagination: { next, previous } }
 *
 * Since apiClient.get<T>() wraps in ApiResponse<T>, use T[] as the generic
 * for paginated endpoints. The pagination metadata is available on the raw
 * response but not typed through ApiResponse.
 *
 * For consumers that need pagination cursors, cast the response:
 *   const res = await api.list() as unknown as PaginatedApiResponse<Item>;
 */
export interface PaginatedApiResponse<T> {
  success: true;
  data: T[];
  pagination: {
    next: string | null;
    previous: string | null;
  };
}

/** @deprecated Use T[] as apiClient generic, or PaginatedApiResponse for full shape */
export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  pagination: {
    next: string | null;
    previous: string | null;
  };
}
