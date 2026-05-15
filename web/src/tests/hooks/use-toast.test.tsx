import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useToast } from "@/hooks/use-toast";

const mockSuccess = vi.fn();
const mockError = vi.fn();
const mockInfo = vi.fn();
const mockDismiss = vi.fn();

vi.mock("sonner", () => ({
  toast: {
    success: (...args: unknown[]) => mockSuccess(...args),
    error: (...args: unknown[]) => mockError(...args),
    info: (...args: unknown[]) => mockInfo(...args),
    dismiss: (...args: unknown[]) => mockDismiss(...args),
  },
}));

describe("useToast", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("calls success with default duration 3000", () => {
    const { result } = renderHook(() => useToast());
    result.current.success("ok");
    expect(mockSuccess).toHaveBeenCalledWith("ok", { duration: 3000 });
  });

  it("calls error with explicit duration override", () => {
    const { result } = renderHook(() => useToast());
    result.current.error("bad", { duration: 5000 });
    expect(mockError).toHaveBeenCalledWith("bad", { duration: 5000 });
  });

  it("calls info and dismiss", () => {
    const { result } = renderHook(() => useToast());
    result.current.info("hello");
    result.current.dismiss("id-1");
    expect(mockInfo).toHaveBeenCalledWith("hello", { duration: 3000 });
    expect(mockDismiss).toHaveBeenCalledWith("id-1");
  });
});
