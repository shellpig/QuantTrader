// API client (Phase 10-B)
// Wraps fetch: base URL, error handling, TypeScript generics

const BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Error type
// ---------------------------------------------------------------------------

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly code: string | undefined,
    message: string | undefined,
  ) {
    super(message ?? `HTTP ${status}`);
    this.name = "ApiClientError";
  }
}

// ---------------------------------------------------------------------------
// Response envelope
// ---------------------------------------------------------------------------

export interface ApiResponse<T> {
  data: T;
  meta: Record<string, unknown>;
}

// ---------------------------------------------------------------------------
// Core fetch wrapper
// ---------------------------------------------------------------------------

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new ApiClientError(
      res.status,
      body?.error?.code as string | undefined,
      body?.error?.message as string | undefined,
    );
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Typed helpers
// ---------------------------------------------------------------------------

export async function apiGet<T>(path: string): Promise<ApiResponse<T>> {
  return apiFetch<ApiResponse<T>>(path);
}

export async function apiPost<T>(
  path: string,
  body: unknown,
): Promise<ApiResponse<T>> {
  return apiFetch<ApiResponse<T>>(path, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export async function apiPut<T>(
  path: string,
  body: unknown,
): Promise<ApiResponse<T>> {
  return apiFetch<ApiResponse<T>>(path, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export async function apiDelete<T>(path: string): Promise<ApiResponse<T>> {
  return apiFetch<ApiResponse<T>>(path, { method: "DELETE" });
}
