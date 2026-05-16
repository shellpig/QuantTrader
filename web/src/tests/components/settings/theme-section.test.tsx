// Tests for ThemeSection component (Phase 10-G-2)

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockSetTheme = vi.fn();
let mockTheme: "dark" | "light" = "dark";

vi.mock("@/components/theme-provider", () => ({
  useTheme: () => ({ theme: mockTheme, setTheme: mockSetTheme }),
}));

import { ThemeSection } from "@/components/settings/theme-section";

describe("ThemeSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockTheme = "dark";
  });

  it("renders theme toggle button", () => {
    render(<ThemeSection />);
    expect(screen.getByTestId("theme-toggle")).toBeInTheDocument();
  });

  it("shows 深色 label when theme is dark", () => {
    render(<ThemeSection />);
    expect(screen.getByText("深色")).toBeInTheDocument();
  });

  it("shows 淺色 label when theme is light", () => {
    mockTheme = "light";
    render(<ThemeSection />);
    expect(screen.getByText("淺色")).toBeInTheDocument();
  });

  it("calls setTheme('light') when dark and toggle is clicked", () => {
    mockTheme = "dark";
    render(<ThemeSection />);
    fireEvent.click(screen.getByTestId("theme-toggle"));
    expect(mockSetTheme).toHaveBeenCalledWith("light");
  });

  it("calls setTheme('dark') when light and toggle is clicked", () => {
    mockTheme = "light";
    render(<ThemeSection />);
    fireEvent.click(screen.getByTestId("theme-toggle"));
    expect(mockSetTheme).toHaveBeenCalledWith("dark");
  });

  it("toggle has aria-checked true in dark mode", () => {
    mockTheme = "dark";
    render(<ThemeSection />);
    expect(screen.getByTestId("theme-toggle")).toHaveAttribute("aria-checked", "true");
  });

  it("toggle has aria-checked false in light mode", () => {
    mockTheme = "light";
    render(<ThemeSection />);
    expect(screen.getByTestId("theme-toggle")).toHaveAttribute("aria-checked", "false");
  });
});
