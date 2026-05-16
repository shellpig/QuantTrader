import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { SweepHeatmap } from "@/components/backtest/SweepHeatmap";
import type { SweepResultRow } from "@/components/backtest/sweep-types";

const TWO_PARAM_ROWS: SweepResultRow[] = [
  {
    params: { short_window: 5, long_window: 40 },
    total_return: 0.1,
    annual_return: 0.03,
    max_drawdown: -0.08,
    sharpe_ratio: 0.6,
    win_rate: 0.5,
    profit_factor: 1.2,
    total_trades: 8,
    error: null,
    sample_warning: false,
  },
  {
    params: { short_window: 10, long_window: 40 },
    total_return: 0.15,
    annual_return: 0.05,
    max_drawdown: -0.07,
    sharpe_ratio: 1.0,
    win_rate: 0.55,
    profit_factor: 1.5,
    total_trades: 9,
    error: null,
    sample_warning: false,
  },
];

const THREE_PARAM_ROWS: SweepResultRow[] = [
  {
    params: { period: 14, oversold: 30, overbought: 70 },
    total_return: 0.1,
    annual_return: 0.03,
    max_drawdown: -0.08,
    sharpe_ratio: 0.6,
    win_rate: 0.5,
    profit_factor: 1.2,
    total_trades: 8,
    error: null,
    sample_warning: false,
  },
];

describe("SweepHeatmap", () => {
  it("renders heatmap only when param dimension is 2", () => {
    const { rerender } = render(<SweepHeatmap rows={TWO_PARAM_ROWS} />);
    expect(screen.getByTestId("sweep-heatmap")).toBeInTheDocument();
    rerender(<SweepHeatmap rows={THREE_PARAM_ROWS} />);
    expect(screen.queryByTestId("sweep-heatmap")).not.toBeInTheDocument();
  });

  it("shows tooltip on cell hover", () => {
    render(<SweepHeatmap rows={TWO_PARAM_ROWS} />);
    const cell = screen.getAllByTestId("sweep-heatmap-cell")[0];
    fireEvent.mouseEnter(cell);
    expect(screen.getByTestId("sweep-heatmap-tooltip")).toBeInTheDocument();
  });

  it("calls copy callback when cell clicked", () => {
    const onCopy = vi.fn();
    render(<SweepHeatmap rows={TWO_PARAM_ROWS} onCopyParams={onCopy} />);
    const cell = screen.getAllByTestId("sweep-heatmap-cell")[0];
    fireEvent.click(cell);
    expect(onCopy).toHaveBeenCalledTimes(1);
  });
});
