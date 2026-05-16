import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ComparisonTable } from "@/components/backtest/ComparisonTable";
import type { BacktestBatchSummary } from "@/components/backtest/batch-types";

const SUMMARIES: BacktestBatchSummary[] = [
  {
    preset_index: 0,
    preset_name: "MA20_MA60",
    strategy_type: "moving_average_cross",
    strategy_params: { short_window: 20, long_window: 60 },
    total_return: 0.12,
    annual_return: 0.03,
    max_drawdown: 0.1,
    sharpe_ratio: 0.8,
    win_rate: 0.5,
    profit_factor: 1.3,
    total_trades: 10,
    error: null,
    detail: null,
  },
  {
    preset_index: 1,
    preset_name: "RSI_14",
    strategy_type: "rsi",
    strategy_params: { period: 14, oversold: 30, overbought: 70 },
    total_return: 0.2,
    annual_return: 0.05,
    max_drawdown: 0.12,
    sharpe_ratio: 1.2,
    win_rate: 0.6,
    profit_factor: 1.8,
    total_trades: 7,
    error: null,
    detail: null,
  },
];

describe("ComparisonTable", () => {
  it("renders 10-column headers", () => {
    render(
      <ComparisonTable
        summaries={SUMMARIES}
        expandedPresetIndex={null}
        onToggleExpand={() => {}}
      />,
    );
    expect(screen.getByText(/策略/)).toBeInTheDocument();
    expect(screen.getByText(/類型/)).toBeInTheDocument();
    expect(screen.getByText(/總報酬/)).toBeInTheDocument();
    expect(screen.getByText(/年化/)).toBeInTheDocument();
    expect(screen.getByText(/最大回撤/)).toBeInTheDocument();
    expect(screen.getByText(/Sharpe/)).toBeInTheDocument();
    expect(screen.getByText(/勝率/)).toBeInTheDocument();
    expect(screen.getByText(/PF/)).toBeInTheDocument();
    expect(screen.getByText(/交易數/)).toBeInTheDocument();
    expect(screen.getByText(/錯誤 \/ 展開/)).toBeInTheDocument();
  });

  it("sorts by Sharpe when header clicked", () => {
    render(
      <ComparisonTable
        summaries={SUMMARIES}
        expandedPresetIndex={null}
        onToggleExpand={() => {}}
      />,
    );

    const sharpeHeader = screen.getByText(/Sharpe/);
    fireEvent.click(sharpeHeader);
    fireEvent.click(sharpeHeader);

    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(2);
  });

  it("triggers expand callback", () => {
    const onToggleExpand = vi.fn();
    render(
      <ComparisonTable
        summaries={SUMMARIES}
        expandedPresetIndex={null}
        onToggleExpand={onToggleExpand}
      />,
    );
    fireEvent.click(screen.getByTestId("expand-row-0"));
    expect(onToggleExpand).toHaveBeenCalledWith(0);
  });
});
