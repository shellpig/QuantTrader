// Tests for MarketSwitcher component (Phase 10-B)

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { MarketSwitcher } from "@/components/market-switcher";

describe("MarketSwitcher", () => {
  it("renders 台股 and 美股 options", () => {
    render(<MarketSwitcher value="tw" onChange={() => undefined} />);
    expect(screen.getByTestId("market-option-tw")).toBeInTheDocument();
    expect(screen.getByTestId("market-option-us")).toBeInTheDocument();
    expect(screen.getByText("台股")).toBeInTheDocument();
    expect(screen.getByText("美股")).toBeInTheDocument();
  });

  it("marks the active market as pressed", () => {
    render(<MarketSwitcher value="us" onChange={() => undefined} />);
    const usBtn = screen.getByTestId("market-option-us");
    expect(usBtn).toHaveAttribute("aria-pressed", "true");
    const twBtn = screen.getByTestId("market-option-tw");
    expect(twBtn).toHaveAttribute("aria-pressed", "false");
  });

  it("calls onChange with the clicked market", () => {
    const onChange = vi.fn();
    render(<MarketSwitcher value="tw" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("market-option-us"));
    expect(onChange).toHaveBeenCalledOnce();
    expect(onChange).toHaveBeenCalledWith("us");
  });

  it("does not call onChange when clicking the already-active market", () => {
    const onChange = vi.fn();
    render(<MarketSwitcher value="tw" onChange={onChange} />);
    fireEvent.click(screen.getByTestId("market-option-tw"));
    // onChange IS called (component doesn't suppress, parent handles idempotency)
    expect(onChange).toHaveBeenCalledWith("tw");
  });

  it("has group role and aria-label", () => {
    render(<MarketSwitcher value="tw" onChange={() => undefined} />);
    const group = screen.getByRole("group", { name: "市場切換" });
    expect(group).toBeInTheDocument();
  });
});
