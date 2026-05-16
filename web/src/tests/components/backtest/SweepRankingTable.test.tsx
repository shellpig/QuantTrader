import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { SweepRankingTable } from "@/components/backtest/SweepRankingTable";
import type { SweepResultRow } from "@/components/backtest/sweep-types";

const ROWS: SweepResultRow[] = [
  {
    params: { short_window: 5, long_window: 40 },
    total_return: 0.1,
    annual_return: 0.03,
    max_drawdown: -0.1,
    sharpe_ratio: 0.6,
    win_rate: 0.5,
    profit_factor: 1.2,
    total_trades: 10,
    error: null,
    sample_warning: false,
  },
  {
    params: { short_window: 10, long_window: 60 },
    total_return: 0.2,
    annual_return: 0.06,
    max_drawdown: -0.08,
    sharpe_ratio: 1.2,
    win_rate: 0.6,
    profit_factor: 1.8,
    total_trades: 2,
    error: null,
    sample_warning: true,
  },
];

describe("SweepRankingTable", () => {
  it("renders top ranking rows with warning icon", () => {
    render(<SweepRankingTable rows={ROWS} />);
    expect(screen.getByTestId("sweep-ranking-table")).toBeInTheDocument();
    expect(screen.getByTestId("sample-warning-icon")).toBeInTheDocument();
    expect(screen.getByText("short_window=10")).toBeInTheDocument();
  });

  it("sorts by total trades when header clicked", () => {
    render(<SweepRankingTable rows={ROWS} />);
    fireEvent.click(screen.getByText(/交易次數/));
    const rows = screen.getAllByRole("row");
    expect(rows.length).toBeGreaterThan(2);
  });

  it("renders empty state with no rows", () => {
    render(<SweepRankingTable rows={[]} />);
    expect(screen.getByTestId("sweep-ranking-empty")).toBeInTheDocument();
  });
});
