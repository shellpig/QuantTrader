import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DividendHistoryPanel } from "@/components/dashboard/p11/dividend-history-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("DividendHistoryPanel", () => {
  it("renders 4-column header and data rows", () => {
    render(
      <DividendHistoryPanel
        data={{
          symbol: "2330",
          market: "tw",
          items: [
            { date: "2026-06-15", cash_dividend: 3.5, stock_dividend: 0.0, ttm_pe: 12.5 },
            { date: "2025-06-17", cash_dividend: 3.2, stock_dividend: 0.0, ttm_pe: 11.4 },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("p11-panel-historical-dividend-pe")).toBeInTheDocument();
    expect(screen.getByText("歷史除息本益比")).toBeInTheDocument();
    expect(screen.getByText("除息日")).toBeInTheDocument();
    expect(screen.queryByText("發放日")).not.toBeInTheDocument();
    expect(screen.getByText("現金股息")).toBeInTheDocument();
    expect(screen.getByText("股票股利")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.historical_dividend_pe)).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.ttm_pe)).toBeInTheDocument();
    expect(screen.getByText("2026-06-15")).toBeInTheDocument();
    expect(screen.getByText("3.50")).toBeInTheDocument();
    expect(screen.getByText("12.50")).toBeInTheDocument();
  });

  it("shows stock_dividend value when non-zero", () => {
    render(
      <DividendHistoryPanel
        data={{
          symbol: "3293",
          market: "tw",
          items: [
            { date: "2024-07-24", cash_dividend: 35.0, stock_dividend: 10.0, ttm_pe: 8.5 },
          ],
        }}
      />,
    );

    expect(screen.getByText("35.00")).toBeInTheDocument();
    expect(screen.getByText("10.00")).toBeInTheDocument();
  });

  it("shows 0.00 for stock_dividend when zero or null", () => {
    render(
      <DividendHistoryPanel
        data={{
          symbol: "2330",
          market: "tw",
          items: [
            { date: "2026-06-15", cash_dividend: 3.5, stock_dividend: 0.0, ttm_pe: 12.5 },
            { date: "2025-06-17", cash_dividend: 3.2, ttm_pe: 11.4 },
          ],
        }}
      />,
    );

    // Both rows should show "0.00" for stock_dividend (0.0 and undefined/null)
    expect(screen.getAllByText("0.00").length).toBeGreaterThanOrEqual(2);
  });

  it("renders placeholder rows when there is no data", () => {
    render(<DividendHistoryPanel data={{ symbol: "2330", market: "tw", items: [] }} />);
    // 5 empty rows × 4 columns = 20 dashes
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(20);
  });
});
