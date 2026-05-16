// Tests for WfaSummaryCards component (Phase 10-E-4)

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WfaSummaryCards } from "@/components/backtest/WfaSummaryCards";

const BASE_AGGREGATE = {
  oos_total_return: 0.12,
  oos_annual_return: null,
  oos_max_drawdown: -0.08,
  oos_sharpe_ratio: 0.75,
  oos_win_rate: 0.67,
  avg_degradation: -0.25,
};

describe("WfaSummaryCards", () => {
  it("renders 5 metric cards", () => {
    render(
      <WfaSummaryCards
        aggregate={BASE_AGGREGATE}
        validWindowCount={6}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    const cards = screen.getAllByTestId("wfa-metric-card");
    expect(cards).toHaveLength(5);
  });

  it("shows oos_total_return as percentage", () => {
    render(
      <WfaSummaryCards
        aggregate={BASE_AGGREGATE}
        validWindowCount={6}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    expect(screen.getByText("12.00%")).toBeInTheDocument();
  });

  it("shows oos_sharpe_ratio formatted to 2 decimals", () => {
    render(
      <WfaSummaryCards
        aggregate={BASE_AGGREGATE}
        validWindowCount={6}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    expect(screen.getByText("0.75")).toBeInTheDocument();
  });

  it("shows degradation chip with negative value", () => {
    render(
      <WfaSummaryCards
        aggregate={BASE_AGGREGATE}
        validWindowCount={6}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    const chip = screen.getByTestId("wfa-degradation-chip");
    expect(chip).toBeInTheDocument();
    expect(chip.textContent).toContain("-0.2500");
  });

  it("shows — when value is null", () => {
    const aggregate = { ...BASE_AGGREGATE, oos_total_return: null };
    render(
      <WfaSummaryCards
        aggregate={aggregate}
        validWindowCount={3}
        totalWindowCount={4}
        currency="USD"
      />,
    );
    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
  });

  it("shows valid / total window counts", () => {
    render(
      <WfaSummaryCards
        aggregate={BASE_AGGREGATE}
        validWindowCount={5}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    expect(screen.getByText("5 / 6")).toBeInTheDocument();
  });

  it("renders without degradation chip when avg_degradation is null", () => {
    const aggregate = { ...BASE_AGGREGATE, avg_degradation: null };
    render(
      <WfaSummaryCards
        aggregate={aggregate}
        validWindowCount={6}
        totalWindowCount={6}
        currency="TWD"
      />,
    );
    expect(screen.queryByTestId("wfa-degradation-chip")).not.toBeInTheDocument();
  });
});
