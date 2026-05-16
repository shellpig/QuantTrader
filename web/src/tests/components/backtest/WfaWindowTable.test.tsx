// Tests for WfaWindowTable component (Phase 10-E-4)

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { WfaWindowTable } from "@/components/backtest/WfaWindowTable";
import type { WfaWindowRow } from "@/components/backtest/WfaWindowTable";

const BASE_WINDOW: WfaWindowRow = {
  window_id: 1,
  is_start: "2018-01-01",
  is_end: "2018-12-31",
  oos_start: "2019-01-01",
  oos_end: "2019-03-31",
  best_params: { short_window: 20, long_window: 60 },
  is_metrics: { sharpe_ratio: 1.2, total_return: 0.15 },
  oos_metrics: { sharpe_ratio: 0.7, total_return: 0.05 },
  degradation: -0.5,
  skipped: false,
  warnings: [],
};

describe("WfaWindowTable", () => {
  it("renders table with data-testid", () => {
    render(<WfaWindowTable windows={[BASE_WINDOW]} />);
    expect(screen.getByTestId("wfa-window-table")).toBeInTheDocument();
  });

  it("renders one row per window", () => {
    const windows: WfaWindowRow[] = [
      BASE_WINDOW,
      { ...BASE_WINDOW, window_id: 2, is_start: "2019-01-01", oos_start: "2020-01-01", oos_end: "2020-03-31", is_end: "2019-12-31" },
    ];
    render(<WfaWindowTable windows={windows} />);
    expect(screen.getByTestId("wfa-window-row-1")).toBeInTheDocument();
    expect(screen.getByTestId("wfa-window-row-2")).toBeInTheDocument();
  });

  it("displays best_params as chips", () => {
    render(<WfaWindowTable windows={[BASE_WINDOW]} />);
    expect(screen.getByText("short_window=20")).toBeInTheDocument();
    expect(screen.getByText("long_window=60")).toBeInTheDocument();
  });

  it("shows degradation in red when < -0.3", () => {
    render(<WfaWindowTable windows={[BASE_WINDOW]} />);
    const cell = screen.getByTestId("degradation-1");
    expect(cell.className).toContain("red");
  });

  it("does NOT show red for degradation > -0.3", () => {
    const window = { ...BASE_WINDOW, degradation: -0.1 };
    render(<WfaWindowTable windows={[window]} />);
    const cell = screen.getByTestId("degradation-1");
    expect(cell.className).not.toContain("red");
  });

  it("shows warning text when warnings present", () => {
    const window = { ...BASE_WINDOW, warnings: ["OOS 交易樣本不足"] };
    render(<WfaWindowTable windows={[window]} />);
    expect(screen.getByText(/OOS 交易樣本不足/)).toBeInTheDocument();
  });

  it("shows skipped state for skipped windows", () => {
    const window = { ...BASE_WINDOW, skipped: true, best_params: null };
    render(<WfaWindowTable windows={[window]} />);
    expect(screen.getByText("已跳過")).toBeInTheDocument();
  });

  it("shows empty state when no windows", () => {
    render(<WfaWindowTable windows={[]} />);
    expect(screen.getByText("尚無視窗結果")).toBeInTheDocument();
  });
});
