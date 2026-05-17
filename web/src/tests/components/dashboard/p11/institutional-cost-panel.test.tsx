import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { InstitutionalCostPanel } from "@/components/dashboard/p11/institutional-cost-panel";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("InstitutionalCostPanel", () => {
  it("renders three institutional rows", () => {
    render(
      <InstitutionalCostPanel
        data={{
          symbol: "2330",
          market: "tw",
          days: 30,
          current_price: 110,
          foreign: { cost: 100, pnl: 10 },
          trust: { cost: 95, pnl: 15 },
          dealer: { cost: 120, pnl: -10 },
        }}
      />,
    );

    expect(screen.getByTestId("p11-panel-institutional-cost")).toBeInTheDocument();
    expect(screen.getByText("外資")).toBeInTheDocument();
    expect(screen.getByText("投信")).toBeInTheDocument();
    expect(screen.getByText("自營商")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.institutional_cost)).toBeInTheDocument();
  });

  it("renders null values as em dash and uses pnl colors", () => {
    render(
      <InstitutionalCostPanel
        data={{
          symbol: "2330",
          market: "tw",
          days: 30,
          current_price: 110,
          foreign: { cost: null, pnl: null },
          trust: { cost: 95, pnl: 5 },
          dealer: { cost: 120, pnl: -5 },
        }}
      />,
    );

    expect(screen.getAllByText("—").length).toBeGreaterThan(0);
    expect(screen.getByTestId("p11-institutional-pnl-trust").className).toContain("text-rise");
    expect(screen.getByTestId("p11-institutional-pnl-dealer").className).toContain("text-fall");
  });
});
