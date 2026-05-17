import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MonthlyRevenuePanel } from "@/components/dashboard/p11/monthly-revenue-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("MonthlyRevenuePanel", () => {
  it("renders monthly metrics, colors, and sparkline bars", () => {
    render(
      <MonthlyRevenuePanel
        data={{
          symbol: "2330",
          market: "tw",
          latest_month: "2026-04",
          latest_revenue: 300_000_000_000,
          items: Array.from({ length: 12 }, (_, i) => ({
            date: `2026-${String(i + 1).padStart(2, "0")}-10`,
            revenue: 200_000_000_000 + i * 1_000_000_000,
            revenue_year: 2026,
            revenue_month: i + 1,
            yoy: i === 11 ? 10.2 : 5 + i,
            mom: i === 11 ? -2.5 : i - 2,
          })),
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
    expect(bars[bars.length - 1].className).toContain("bg-primary");
  });

  it("renders placeholders for missing dataset", () => {
    render(<MonthlyRevenuePanel data={undefined} />);
    const sparkline = screen.getByTestId("p11-monthly-revenue-sparkline");
    expect(sparkline.querySelectorAll("div").length).toBe(12);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });
});
