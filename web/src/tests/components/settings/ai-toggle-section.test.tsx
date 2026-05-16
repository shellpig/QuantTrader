// Tests for AiToggleSection component (Phase 10-G-2)

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { AiToggleSection } from "@/components/settings/ai-toggle-section";

// Radix Tooltip uses portals
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

describe("AiToggleSection", () => {
  it("renders the disabled AI toggle button", () => {
    render(<AiToggleSection />);
    const toggle = screen.getByTestId("ai-toggle");
    expect(toggle).toBeInTheDocument();
    expect(toggle).toBeDisabled();
  });

  it("toggle has aria-checked false (always off)", () => {
    render(<AiToggleSection />);
    expect(screen.getByTestId("ai-toggle")).toHaveAttribute("aria-checked", "false");
  });

  it("shows 永久停用 label", () => {
    render(<AiToggleSection />);
    expect(screen.getByText("（永久停用）")).toBeInTheDocument();
  });

  it("renders section heading", () => {
    render(<AiToggleSection />);
    expect(screen.getByText("AI 分析")).toBeInTheDocument();
  });
});
