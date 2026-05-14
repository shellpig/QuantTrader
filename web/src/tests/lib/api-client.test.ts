// Tests for api-client (Phase 10-B)

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ApiClientError, apiFetch } from "@/lib/api-client";

describe("ApiClientError", () => {
  it("is an instance of Error", () => {
    const err = new ApiClientError(404, "NOT_FOUND", "Not found");
    expect(err).toBeInstanceOf(Error);
    expect(err.name).toBe("ApiClientError");
    expect(err.status).toBe(404);
    expect(err.code).toBe("NOT_FOUND");
    expect(err.message).toBe("Not found");
  });

  it("falls back to HTTP status message when message is undefined", () => {
    const err = new ApiClientError(500, undefined, undefined);
    expect(err.message).toBe("HTTP 500");
  });
});

describe("apiFetch", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    global.fetch = vi.fn();
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("returns parsed JSON on success", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({ data: { status: "ok" } }),
    } as Response);

    const result = await apiFetch<{ data: { status: string } }>("/api/health");
    expect(result).toEqual({ data: { status: "ok" } });
  });

  it("throws ApiClientError on non-ok response with error body", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 422,
      json: async () => ({
        error: { code: "WHITELIST_REJECTED", message: "Key not allowed" },
      }),
    } as Response);

    await expect(apiFetch("/api/config")).rejects.toMatchObject({
      name: "ApiClientError",
      status: 422,
      code: "WHITELIST_REJECTED",
      message: "Key not allowed",
    });
  });

  it("throws ApiClientError when error body is unparseable", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: false,
      status: 503,
      json: async () => { throw new Error("JSON parse error"); },
    } as unknown as Response);

    const err = await apiFetch("/api/health").catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiClientError);
    expect((err as ApiClientError).status).toBe(503);
  });

  it("includes Content-Type header in requests", async () => {
    (global.fetch as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      ok: true,
      json: async () => ({}),
    } as Response);

    await apiFetch("/api/health");

    const [, opts] = (global.fetch as ReturnType<typeof vi.fn>).mock.calls[0] as [string, RequestInit];
    const headers = opts.headers as Record<string, string>;
    expect(headers["Content-Type"]).toBe("application/json");
  });
});
