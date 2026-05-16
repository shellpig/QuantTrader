// Tests for WfaStabilityTable component (Phase 10-E-4)

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WfaStabilityTable } from "@/components/backtest/WfaStabilityTable";

const STABLE_PARAMS = {
  short_window: {
    values: [20, 20, 20],
    cv: 0.0,
    mean: 20.0,
    std: 0.0,
    status: "stable",
  },
  long_window: {
    values: [60, 60, 80],
    cv: 0.18,
    mean: 66.67,
    std: 9.43,
    status: "moderate",
  },
  entry_period: {
    values: [10, 20, 55],
    cv: 0.72,
    mean: 28.33,
    std: 19.01,
    status: "unstable",
  },
};

describe("WfaStabilityTable", () => {
  it("renders table with data-testid", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    expect(screen.getByTestId("wfa-stability-table")).toBeInTheDocument();
  });

  it("renders one row per param", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    expect(screen.getByTestId("stability-row-short_window")).toBeInTheDocument();
    expect(screen.getByTestId("stability-row-long_window")).toBeInTheDocument();
    expect(screen.getByTestId("stability-row-entry_period")).toBeInTheDocument();
  });

  it("shows 穩定 label for cv < 0.2", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    const label = screen.getByTestId("stability-label-short_window");
    expect(label.textContent).toBe("穩定");
    expect(label.className).toContain("green");
  });

  it("shows 中等 label for 0.2 <= cv < 0.5", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    const label = screen.getByTestId("stability-label-long_window");
    expect(label.textContent).toBe("中等");
    expect(label.className).toContain("amber");
  });

  it("shows 不穩定 label for cv >= 0.5", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    const label = screen.getByTestId("stability-label-entry_period");
    expect(label.textContent).toBe("不穩定");
    expect(label.className).toContain("red");
  });

  it("shows value chips for each window's value", () => {
    render(<WfaStabilityTable params={STABLE_PARAMS} />);
    // short_window values: 20, 20, 20
    const chips = screen.getAllByText("20");
    expect(chips.length).toBeGreaterThanOrEqual(3);
  });

  it("shows empty state when no params", () => {
    render(<WfaStabilityTable params={{}} />);
    expect(screen.getByText("尚無穩定性資料")).toBeInTheDocument();
  });
});
