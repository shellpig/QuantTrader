// Tests for use-config hook (Phase 10-G-2)

import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { SWRConfig } from "swr";

// Mock api-client module
const mockApiFetch = vi.fn();
const mockApiPut = vi.fn();
const mockApiPost = vi.fn();
const mockApiDeleteNoContent = vi.fn();

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
  apiPut: (...args: unknown[]) => mockApiPut(...args),
  apiPost: (...args: unknown[]) => mockApiPost(...args),
  apiDeleteNoContent: (...args: unknown[]) => mockApiDeleteNoContent(...args),
  ApiClientError: class ApiClientError extends Error {
    constructor(
      public status: number,
      public code: string | undefined,
      message: string | undefined,
    ) {
      super(message);
    }
  },
}));

import {
  useSecretsStatus,
  useStrategyPresets,
  updateSecrets,
  upsertStrategyPreset,
  deleteStrategyPreset,
  restoreStrategyDefaults,
} from "@/hooks/use-config";

// Fresh SWR cache per test — prevents deduplication across tests
function freshWrapper({ children }: { children: React.ReactNode }) {
  return React.createElement(
    SWRConfig,
    { value: { provider: () => new Map() } },
    children,
  );
}

describe("useSecretsStatus", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns status from API", async () => {
    mockApiFetch.mockResolvedValueOnce({
      data: { openai: true, anthropic: false, gemini: false, finmind: false, google: false },
    });

    const { result } = renderHook(() => useSecretsStatus(), { wrapper: freshWrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.status.openai).toBe(true);
    expect(result.current.status.anthropic).toBe(false);
  });

  it("defaults to empty object on error", async () => {
    mockApiFetch.mockRejectedValueOnce(new Error("network error"));

    const { result } = renderHook(() => useSecretsStatus(), { wrapper: freshWrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.status).toEqual({});
  });
});

describe("useStrategyPresets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns presets from API", async () => {
    mockApiFetch.mockResolvedValueOnce({
      data: [{ name: "MA Cross", type: "moving_average_cross", params: { short_window: 20, long_window: 60 } }],
    });

    const { result } = renderHook(() => useStrategyPresets(), { wrapper: freshWrapper });

    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.presets).toHaveLength(1);
    expect(result.current.presets[0].name).toBe("MA Cross");
  });

  it("defaults to empty array on error", async () => {
    mockApiFetch.mockRejectedValueOnce(new Error("network error"));

    const { result } = renderHook(() => useStrategyPresets(), { wrapper: freshWrapper });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(result.current.presets).toEqual([]);
  });
});

describe("updateSecrets", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiPut with correct path and payload", async () => {
    mockApiPut.mockResolvedValueOnce({ data: { updated: true }, meta: {} });

    await updateSecrets({ openai: "sk-test" });

    expect(mockApiPut).toHaveBeenCalledWith("/api/config/secrets", { keys: { openai: "sk-test" } });
  });
});

describe("upsertStrategyPreset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiPost with preset and returns name", async () => {
    mockApiPost.mockResolvedValueOnce({ data: { upserted: true, name: "TestMA" }, meta: {} });

    const result = await upsertStrategyPreset({
      name: "TestMA",
      type: "moving_average_cross",
      params: { short_window: 20, long_window: 60 },
    });

    expect(result.name).toBe("TestMA");
    expect(mockApiPost).toHaveBeenCalledWith(
      "/api/config/strategies",
      expect.objectContaining({ preset: expect.objectContaining({ name: "TestMA" }) }),
    );
  });
});

describe("deleteStrategyPreset", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls apiDeleteNoContent with encoded name", async () => {
    mockApiDeleteNoContent.mockResolvedValueOnce(undefined);

    await deleteStrategyPreset("MA Cross");

    expect(mockApiDeleteNoContent).toHaveBeenCalledWith(
      "/api/config/strategies/MA%20Cross",
    );
  });
});

describe("restoreStrategyDefaults", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls restore endpoint and returns count", async () => {
    mockApiPost.mockResolvedValueOnce({ data: { count: 8 }, meta: {} });

    const count = await restoreStrategyDefaults();

    expect(count).toBe(8);
    expect(mockApiPost).toHaveBeenCalledWith("/api/config/strategies/restore", {});
  });
});
