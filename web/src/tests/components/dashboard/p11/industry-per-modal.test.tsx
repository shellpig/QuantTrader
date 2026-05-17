import { fireEvent, render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { IndustryPerModal } from "@/components/dashboard/p11/industry-per-modal";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";

describe("IndustryPerModal", () => {
  const sampleData = {
    symbol: "2330",
    market: "tw" as const,
    industry: "半導體",
    median: 18,
    mean: 19,
    count: 3,
    cached_at: "2026-05-17T10:00:00+08:00",
    items: [
      { symbol: "2330", name: "台積電", date: "2026-05-17", per: 20, pbr: 4, dividend_yield: 2, is_current: true },
      { symbol: "2303", name: "聯電", date: "2026-05-17", per: 16, pbr: 2.5, dividend_yield: 3, is_current: false },
      { symbol: "2454", name: "聯發科", date: "2026-05-17", per: 24, pbr: 5, dividend_yield: 1.5, is_current: false },
    ],
  };

  it("renders summary, chinese labels, target marker, and sortable rows", () => {
    render(<IndustryPerModal open onOpenChange={() => undefined} data={sampleData} isLoading={false} />);

    expect(screen.getByText("同產業本益比 · 半導體")).toBeInTheDocument();
    expect(screen.getByText("中位數：")).toBeInTheDocument();
    expect(screen.getByText("平均數：")).toBeInTheDocument();
    expect(screen.getByText("樣本數：")).toBeInTheDocument();
    expect(screen.getByText("快取時間：2026-05-17T10:00:00+08:00")).toBeInTheDocument();
    expect(screen.getByText("本益比")).toBeInTheDocument();
    expect(screen.getByText("股價淨值比")).toBeInTheDocument();
    expect(screen.getByText("← 當前")).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.per_abbr)).toBeInTheDocument();
    expect(screen.getByLabelText(P11_TOOLTIP_TEXT.pbr)).toBeInTheDocument();

    const rows = screen.getAllByRole("row");
    expect(rows[1]).toHaveTextContent("2454");
    fireEvent.click(screen.getByRole("button", { name: /本益比/ }));
    const rowsAsc = screen.getAllByRole("row");
    expect(rowsAsc[1]).toHaveTextContent("2303");
  });

  it("shows loading overlay and keeps table visible beneath", () => {
    render(<IndustryPerModal open onOpenChange={() => undefined} data={sampleData} isLoading />);
    expect(screen.getByText("資料讀取中，正在整理同產業本益比...")).toBeInTheDocument();
    expect(screen.getByText("首次載入約 8-25 秒，完成後會一次更新")).toBeInTheDocument();

    const table = screen.getByRole("table");
    expect(within(table).getByText("2454")).toBeInTheDocument();
  });
});
