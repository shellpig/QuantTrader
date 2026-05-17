import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DividendHistoryPanel } from "@/components/dashboard/p11/dividend-history-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("DividendHistoryPanel", () => {
  it("renders 3-column header and data rows", () => {
    render(
      <DividendHistoryPanel
        data={{
          symbol: "2330",
          market: "tw",
          items: [
            { date: "2026-06-15", cash_dividend: 3.5, ttm_pe: 12.5 },
            { date: "2025-06-17", cash_dividend: 3.2, ttm_pe: 11.4 },
          ],
        }}
      />,
    );

    expect(screen.getByTestId("p11-panel-historical-dividend-pe")).toBeInTheDocument();
    expect(screen.getByText("歷史除息本益比")).toBeInTheDocument();
    expect(screen.getByText("除息日")).toBeInTheDocument();
    expect(screen.queryByText("發放日")).not.toBeInTheDocument();
    expect(screen.getByText("現金股息")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.historical_dividend_pe)).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.ttm_pe)).toBeInTheDocument();
    expect(screen.getByText("2026-06-15")).toBeInTheDocument();
    expect(screen.getByText("3.50")).toBeInTheDocument();
    expect(screen.getByText("12.50")).toBeInTheDocument();
  });

  it("renders placeholder rows when there is no data", () => {
    render(<DividendHistoryPanel data={{ symbol: "2330", market: "tw", items: [] }} />);
    // 5 empty rows × 3 columns = 15 dashes
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(15);
  });
});
