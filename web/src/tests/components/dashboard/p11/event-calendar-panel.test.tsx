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
    expect(screen.getByTestId("p11-shareholder-missing")).toHaveTextContent("撈不到資料，需要手動填入");
    expect(screen.getByTestId("p11-shareholder-missing")).not.toHaveTextContent("ETF");
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

  it("appends ETF note when symbol is an ETF and shareholder data is missing", () => {
    render(
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
          is_etf: true,
        }}
      />,
    );
    expect(screen.getByTestId("p11-shareholder-missing")).toHaveTextContent(
      "撈不到資料，需要手動填入（ETF沒有股東會）",
    );
  });
});
