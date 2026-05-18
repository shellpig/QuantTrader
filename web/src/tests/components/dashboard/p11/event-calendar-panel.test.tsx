import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { EventCalendarPanel } from "@/components/dashboard/p11/event-calendar-panel";

describe("EventCalendarPanel", () => {
  it("renders upcoming/last sections and manual chip", () => {
    const onEdit = vi.fn();
    render(
      <EventCalendarPanel
        onEdit={onEdit}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: { date: "2026-06-20", cash_dividend: 3.5, days_until: 10, is_estimated: false },
          last_ex_dividend: { date: "2025-06-15", cash_dividend: 3.2 },
          next_shareholder_meeting: { date: "2026-06-30", meeting_type: "常會", source: "manual", is_manual: true, days_until: 20 },
          last_shareholder_meeting: { date: "2025-06-25", meeting_type: "常會", source: "auto", is_manual: false },
          missing_shareholder_meeting: false,
        }}
      />,
    );

    expect(screen.getByTestId("p11-panel-event-calendar")).toBeInTheDocument();
    expect(screen.getByText("即將")).toBeInTheDocument();
    expect(screen.getByText("上次")).toBeInTheDocument();
    expect(screen.getByText("[手動設定]")).toBeInTheDocument();
    expect(screen.getByText("倒數 20 天")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText("edit-shareholder-meeting"));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it("shows missing message and does not show countdown in last shareholder row", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: null,
          last_ex_dividend: null,
          next_shareholder_meeting: null,
          last_shareholder_meeting: { date: "2025-06-25", meeting_type: "常會", source: "auto", is_manual: false, days_until: 99 },
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.getByTestId("p11-shareholder-missing")).toBeInTheDocument();
    expect(screen.getByTestId("p11-shareholder-missing")).toHaveTextContent("撈不到股東會資料，需要手動填入（或是ETF沒有股東會）");
    expect(screen.getByTestId("p11-last-shareholder-row")).not.toHaveTextContent("倒數 99 天");
  });

  it("shows stock_dividend in dividend line when > 0", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "3293",
          market: "tw",
          next_ex_dividend: { date: "2026-07-24", cash_dividend: 35.0, stock_dividend: 10.0, days_until: 30, is_estimated: false },
          last_ex_dividend: { date: "2024-07-24", cash_dividend: 35.0, stock_dividend: 10.0 },
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.getAllByText(/股票股利 10\.00/).length).toBeGreaterThanOrEqual(1);
  });

  it("does not show stock_dividend when 0 or absent", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: { date: "2026-06-20", cash_dividend: 3.5, stock_dividend: 0, days_until: 10, is_estimated: false },
          last_ex_dividend: { date: "2025-06-15", cash_dividend: 3.2 },
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.queryByText(/股票股利/)).not.toBeInTheDocument();
  });

  // Phase 11-E: unified missing text regardless of ETF flag
  it("11-E-F4: shows unified missing text regardless of ETF flag", () => {
    for (const isEtf of [true, false, undefined]) {
      const { unmount } = render(
        <EventCalendarPanel
          onEdit={() => undefined}
          data={{
            symbol: "00929",
            market: "tw",
            next_ex_dividend: null,
            last_ex_dividend: null,
            next_shareholder_meeting: null,
            last_shareholder_meeting: null,
            missing_shareholder_meeting: true,
            ...(isEtf !== undefined ? { is_etf: isEtf } : {}),
          }}
        />,
      );
      expect(screen.getByTestId("p11-shareholder-missing")).toHaveTextContent(
        "撈不到股東會資料，需要手動填入（或是ETF沒有股東會）",
      );
      unmount();
    }
  });

  it("11-E-F7: edit button appears after the ? (HelpTooltip), not before it", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: null,
          last_ex_dividend: null,
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: false,
        }}
      />,
    );
    const editBtn = screen.getByTestId("p11-event-calendar-edit-btn");
    // HelpTooltip renders as <span aria-label="..."> not a <button>
    const helpSpan = screen.getByLabelText("事件行事曆整合近期除息日與股東會，協助評估事件前後波動與部位規劃。");
    // helpSpan must precede editBtn in DOM order
    expect(
      helpSpan.compareDocumentPosition(editBtn) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
  });

  // Phase 11-D: Goodinfo dividend policy fallback
  it("11-D-F1: formal next_ex_dividend shows date/cash/stock/countdown, no [預估]", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: { date: "2026-07-15", cash_dividend: 3.5, stock_dividend: 0.0, days_until: 58, is_estimated: false },
          last_ex_dividend: null,
          dividend_policy_fallback: null,
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.getByText("2026-07-15")).toBeInTheDocument();
    expect(screen.getByText(/現金股利 3\.50/)).toBeInTheDocument();
    expect(screen.getByText("倒數 58 天")).toBeInTheDocument();
    expect(screen.queryByText(/\[預估\]/)).not.toBeInTheDocument();
    expect(screen.queryByTestId("p11-dividend-fallback-current")).not.toBeInTheDocument();
  });

  it("11-D-F2: formal entry with stock_dividend=0 does not show stock dividend", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "2330",
          market: "tw",
          next_ex_dividend: { date: "2026-07-15", cash_dividend: 3.5, stock_dividend: 0, days_until: 58, is_estimated: false },
          last_ex_dividend: null,
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.queryByText(/股票股利/)).not.toBeInTheDocument();
  });

  it("11-D-F3: fallback current_year shows undetermined payment period, amounts, link, note, no countdown", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "3293",
          market: "tw",
          next_ex_dividend: null,
          last_ex_dividend: { date: "2025-07-24", cash_dividend: 29.0, stock_dividend: 0.0 },
          dividend_policy_fallback: {
            status: "current_year",
            year: 2026,
            period: "25H2",
            payment_status: "undetermined",
            cash_dividend: 32.0,
            stock_dividend: 10.0,
            source_url: "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=3293",
            source_note: "此為網頁抓取資料，請自行前往來源確認",
          },
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.getByTestId("p11-dividend-fallback-current")).toBeInTheDocument();
    expect(screen.getByText("今年股利資料")).toBeInTheDocument();
    expect(screen.getByText("25H2")).toBeInTheDocument();
    expect(screen.getByText("股利發放時間未定")).toBeInTheDocument();
    expect(screen.getByText(/現金股利 32\.00/)).toBeInTheDocument();
    expect(screen.getByText(/股票股利 10\.00/)).toBeInTheDocument();
    expect(screen.getByTestId("p11-dividend-fallback-link")).toBeInTheDocument();
    expect(screen.getByText(/此為網頁抓取資料/)).toBeInTheDocument();
    // fallback must NOT show countdown
    expect(screen.queryByText(/倒數/)).not.toBeInTheDocument();
  });

  it("11-D-F4: fallback stale/not_found/fetch_failed shows 查無最新股利資料 with link", () => {
    for (const status of ["stale", "not_found", "fetch_failed"] as const) {
      const { unmount } = render(
        <EventCalendarPanel
          onEdit={() => undefined}
          data={{
            symbol: "2330",
            market: "tw",
            next_ex_dividend: null,
            last_ex_dividend: null,
            dividend_policy_fallback: {
              status,
              year: null,
              cash_dividend: null,
              stock_dividend: null,
              source_url: "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=2330",
              source_note: "此為網頁抓取資料，請自行前往來源確認",
            },
            next_shareholder_meeting: null,
            last_shareholder_meeting: null,
            missing_shareholder_meeting: true,
          }}
        />,
      );
      expect(screen.getByTestId("p11-dividend-fallback-not-found")).toBeInTheDocument();
      expect(screen.getByText("查無最新股利資料")).toBeInTheDocument();
      expect(screen.getByTestId("p11-dividend-fallback-link")).toBeInTheDocument();
      unmount();
    }
  });

  it("11-D-F5: Goodinfo fallback does not show countdown", () => {
    render(
      <EventCalendarPanel
        onEdit={() => undefined}
        data={{
          symbol: "3293",
          market: "tw",
          next_ex_dividend: null,
          last_ex_dividend: null,
          dividend_policy_fallback: {
            status: "current_year",
            year: 2026,
            cash_dividend: 32.0,
            stock_dividend: 0.0,
            source_url: "https://goodinfo.tw/tw/StockDividendPolicy.asp?STOCK_ID=3293",
            source_note: "此為網頁抓取資料，請自行前往來源確認",
          },
          next_shareholder_meeting: null,
          last_shareholder_meeting: null,
          missing_shareholder_meeting: true,
        }}
      />,
    );
    expect(screen.queryByText(/倒數/)).not.toBeInTheDocument();
  });
});
