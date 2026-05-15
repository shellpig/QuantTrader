// Tests for useAiStatus hook (Phase 10-F-1)

import { renderHook, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useAiStatus } from "@/hooks/use-ai-status";

const FEATURE_LOCKED_RESPONSE = {
  available: false,
  reason: "feature_locked",
  message: "AI 功能尚未開放，將於後續版本啟用。",
};

beforeEach(() => {
  vi.spyOn(globalThis, "fetch").mockResolvedValue(
    new Response(JSON.stringify(FEATURE_LOCKED_RESPONSE), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("useAiStatus", () => {
  it("returns available=false and reason=feature_locked", async () => {
    const { result } = renderHook(() => useAiStatus());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.status?.available).toBe(false);
    expect(result.current.status?.reason).toBe("feature_locked");
  });

  it("returns message string", async () => {
    const { result } = renderHook(() => useAiStatus());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.status?.message).toMatch(/AI 功能/);
  });

  it("isError is false on success", async () => {
    const { result } = renderHook(() => useAiStatus());
    await waitFor(() => expect(result.current.isLoading).toBe(false));
    expect(result.current.isError).toBe(false);
  });
});
