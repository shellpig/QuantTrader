import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { DividendHistoryPanel } from "@/components/dashboard/p11/dividend-history-panel";
import { IndustryPerModal } from "@/components/dashboard/p11/industry-per-modal";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("P11 tooltip coverage", () => {
  it("keeps abbreviation tooltip dictionary populated", () => {
    expect(P11_TOOLTIP_TEXT.per_abbr).toContain("PER");
    expect(P11_TOOLTIP_TEXT.ttm_pe).toContain("TTM");
    expect(P11_TOOLTIP_TEXT.eps).toContain("EPS");
    expect(P11_TOOLTIP_TEXT.vwap).toContain("VWAP");
  });

  it("renders tooltip triggers for PER/PBR/TTM in P11 components", () => {
    render(
      <>
        <IndustryPerModal
          open
          onOpenChange={() => undefined}
          isLoading={false}
          data={{
            symbol: "2330",
            market: "tw",
            industry: "半導體",
            median: 18,
            mean: 19,
            count: 1,
            cached_at: "2026-05-17T10:00:00+08:00",
            items: [{ symbol: "2330", name: "台積電", date: "2026-05-17", per: 20, pbr: 4, dividend_yield: 2, is_current: true }],
          }}
        />
        <DividendHistoryPanel
          data={{
            symbol: "2330",
            market: "tw",
            items: [{ date: "2026-06-15", cash_dividend: 3.5, ttm_pe: 12.5 }],
          }}
        />
      </>,
    );

    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.per_abbr)).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.pbr)).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.ttm_pe)).toBeInTheDocument();
  });
});
