import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ValuationPanel } from "@/components/dashboard/p11/valuation-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("ValuationPanel", () => {
  it("renders valuation values and opens same-industry modal", () => {
    const onOpenIndustry = vi.fn();
    render(
      <ValuationPanel
        data={{
          symbol: "2330",
          market: "tw",
          date: "2026-05-17",
          per: 20.5,
          pbr: 4.1,
          dividend_yield: 2.3,
          industry: "半導體",
        }}
        onOpenIndustry={onOpenIndustry}
      />,
    );

    expect(screen.getByTestId("p11-panel-pe-ratio")).toBeInTheDocument();
    expect(screen.getAllByText("本益比").length).toBeGreaterThan(0);
    expect(screen.getByText("股價淨值比")).toBeInTheDocument();
    expect(screen.getByText("殖利率")).toBeInTheDocument();
    expect(screen.getByText("20.50")).toBeInTheDocument();
    expect(screen.getByText("4.10")).toBeInTheDocument();
    expect(screen.getByText("2.30%")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.pe_ratio)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "同產業 ->" }));
    expect(onOpenIndustry).toHaveBeenCalledTimes(1);
  });

  it("renders fallback placeholder when data is missing", () => {
    render(<ValuationPanel data={undefined} onOpenIndustry={() => undefined} />);
    expect(screen.getAllByText("—").length).toBeGreaterThanOrEqual(3);
  });

  it("shows unsupported note when all valuation fields are null (ETF)", () => {
    render(
      <ValuationPanel
        data={{ symbol: "0056", market: "tw", date: null, per: null, pbr: null, dividend_yield: null, industry: null }}
        onOpenIndustry={() => undefined}
      />,
    );
    expect(screen.getByTestId("p11-valuation-unsupported")).toBeInTheDocument();
    expect(screen.getByText("資料源未提供此標的估值資料（如 ETF）")).toBeInTheDocument();
    expect(screen.queryByText("股價淨值比")).not.toBeInTheDocument();
  });
});
