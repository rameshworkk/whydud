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

export interface PaginatedResponse<T> {
  success: true;
  data: T[];
  pagination: {
    next: string | null;
    previous: string | null;
  };
}
