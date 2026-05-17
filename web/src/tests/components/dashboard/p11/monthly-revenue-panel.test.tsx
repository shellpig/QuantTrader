import { render, screen, fireEvent } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MonthlyRevenuePanel } from "@/components/dashboard/p11/monthly-revenue-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

const TWELVE_MONTHS_DATA = Array.from({ length: 12 }, (_, i) => ({
  date: `2026-${String(i + 1).padStart(2, "0")}-10`,
  revenue: 200_000_000_000 + i * 1_000_000_000,
  revenue_year: 2026,
  revenue_month: i + 1,
  yoy: i === 11 ? 10.2 : 5 + i,
  mom: i === 11 ? -2.5 : i - 2,
}));

describe("MonthlyRevenuePanel", () => {
  it("renders monthly metrics, colors, and sparkline bars", () => {
    render(
      <MonthlyRevenuePanel
        data={{
          symbol: "2330",
          market: "tw",
          latest_month: "2026-04",
          latest_revenue: 300_000_000_000,
          items: TWELVE_MONTHS_DATA,
        }}
      />,
    );

    expect(screen.getByTestId("p11-panel-monthly-revenue")).toBeInTheDocument();
    expect(screen.getByText("2026-04")).toBeInTheDocument();
    expect(screen.getByText("3,000.0 億")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.monthly_revenue)).toBeInTheDocument();

    const yoy = screen.getByText("10.2%");
    const mom = screen.getByText("-2.5%");
    expect(yoy.className).toContain("text-rise");
    expect(mom.className).toContain("text-fall");

    const sparkline = screen.getByTestId("p11-monthly-revenue-sparkline");
    const bars = sparkline.querySelectorAll("div");
    expect(bars.length).toBe(12);
    expect(bars[bars.length - 1].className).toContain("bg-sky-400");
  });

  it("shows tooltip with month, revenue, yoy, mom on bar mouseenter", () => {
    render(
      <MonthlyRevenuePanel
        data={{
          symbol: "2330",
          market: "tw",
          latest_month: "2026-04",
          latest_revenue: 300_000_000_000,
          items: TWELVE_MONTHS_DATA,
        }}
      />,
    );

    expect(screen.queryByTestId("revenue-bar-tooltip")).not.toBeInTheDocument();

    // Bar 0 (2026-01): revenue = 200B → 2,000.0 億, yoy = +5.0%, mom = -2.0%
    fireEvent.mouseEnter(screen.getByTestId("revenue-bar-0"));
    const tooltip = screen.getByTestId("revenue-bar-tooltip");
    expect(tooltip).toBeInTheDocument();
    expect(tooltip).toHaveTextContent("2026-01");
    expect(tooltip).toHaveTextContent("2,000.0 億");

    // mouseLeave on the sparkline container (not the bar) dismisses the tooltip
    const container = screen.getByTestId("p11-monthly-revenue-sparkline").closest(".relative")!;
    fireEvent.mouseLeave(container);
    expect(screen.queryByTestId("revenue-bar-tooltip")).not.toBeInTheDocument();
  });

  it("renders placeholders for missing dataset", () => {
    render(<MonthlyRevenuePanel data={undefined} />);
    const sparkline = screen.getByTestId("p11-monthly-revenue-sparkline");
    expect(sparkline.querySelectorAll("div").length).toBe(12);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });

  it("shows unsupported note when data is loaded but items is empty (ETF)", () => {
    render(
      <MonthlyRevenuePanel
        data={{ symbol: "0056", market: "tw", latest_month: null, latest_revenue: null, items: [] }}
      />,
    );
    expect(screen.getByTestId("p11-monthly-revenue-unsupported")).toBeInTheDocument();
    expect(screen.getByText("資料源未提供此標的月營收資料（如 ETF）")).toBeInTheDocument();
    expect(screen.queryByTestId("p11-monthly-revenue-sparkline")).not.toBeInTheDocument();
  });
});
