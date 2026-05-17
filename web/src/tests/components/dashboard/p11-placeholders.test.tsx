import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import DashboardPageClient from "@/components/dashboard/dashboard-page-client";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import type { DashboardPayloadResponse, OhlcvBar } from "@/types/analysis";
import type { Market } from "@/types/market";

const mockMutate = vi.fn();
let mockLoading = false;

function buildBars(symbol: string): OhlcvBar[] {
  return [
    {
      date: "2026-05-15T00:00:00+08:00",
      open: 100,
      high: 110,
      low: 95,
      close: 108,
      volume: 1200000,
      symbol,
    },
    {
      date: "2026-05-16T00:00:00+08:00",
      open: 108,
      high: 112,
      low: 104,
      close: 111,
      volume: 1500000,
      symbol,
    },
  ];
}

function buildPayload(market: Market, symbol: string): DashboardPayloadResponse {
  return {
    symbol,
    market,
    subject_name: market === "tw" ? "台積電" : "Apple Inc",
    analysis_time: "2026-05-17 10:00:00",
    ai_enabled: true,
    daily_df: buildBars(symbol),
    technical: {
      trend_direction: "多頭",
      ma_status: "多頭排列",
      kd_status: "黃金交叉",
      macd_status: "多方增強",
      volume_status: "量增",
      volume_price_relation: "價漲量增",
      short_term_score: 0.76,
      short_term_label: "偏多",
      short_term_components: { ma: 0.8, kd: 0.7, volume_price: 0.8, breakout: 0.7 },
      resistance_levels: [
        { value: 533, label: "R1", kind: "swing_high" },
        { value: 30.43, label: "R2", kind: "swing_high" },
      ],
      support_levels: [
        { value: 28.42, label: "S1", kind: "ma20" },
        { value: 23.07, label: "S2", kind: "swing_low" },
      ],
      volume_price_divergence: "無明顯背離",
      ma_bias: "2.1%",
      chip_behavior: "中性",
      operation_observation: "沿 20MA 偏多震盪。",
    },
    candle_patterns: [{ name: "長紅 K", detected: true, description: "多方力道強" }],
    chart_patterns: [{ pattern_type: "W底（雙底）", formed: false, description: "尚未突破", key_points: [] }],
    multi_timeframe: {
      daily: { timeframe: "day", trend_direction: "多頭", strength: "中強" },
      weekly: { timeframe: "week", trend_direction: "多頭", strength: "中等" },
      monthly: { timeframe: "month", trend_direction: "多頭", strength: "中等" },
    },
    quote:
      market === "tw"
        ? {
            symbol,
            name: "台積電",
            price: 111,
            change: 3,
            change_pct: 2.78,
            open: 108,
            high: 112,
            low: 104,
            yesterday_close: 108,
            volume: 30000,
            timestamp: "2026-05-17T10:00:00+08:00",
            trade_date: "2026-05-17",
            best_bid: [110],
            best_ask: [111],
            best_bid_vol: [100, 50],
            best_ask_vol: [90, 45],
            is_market_open: true,
            is_estimated_price: false,
            price_label: "成交價",
            estimated_price: null,
          }
        : null,
    bid_ask: market === "tw" ? { total_bid_vol: 150, total_ask_vol: 135, bid_ratio: 0.53, ask_ratio: 0.47, label: "買方略強" } : null,
    chip:
      market === "tw"
        ? {
            foreign_net_n_days: 1000,
            trust_net_n_days: 200,
            dealer_net_n_days: -100,
            foreign_label: "買超 1,000 張",
            trust_label: "買超 200 張",
            dealer_label: "賣超 100 張",
            chip_concentration: "偏多",
            chip_trend: "集中",
            chip_description: "法人偏多",
            margin_balance_change: 300,
            short_balance_change: -120,
          }
        : null,
    chip_recent_df:
      market === "tw"
        ? [{ 日期: "2026-05-16", 外資: 1200, 投信: 200, 自營商: -100 }]
        : [],
    chip_error: null,
    intraday_df: market === "us" ? buildBars(symbol) : [],
    intraday_snapshot:
      market === "us"
        ? {
            symbol,
            price: 210.5,
            previous_raw_close: 208.2,
            change: 2.3,
            change_pct: 1.1,
            volume: 5200000,
            timestamp: "2026-05-17T10:00:00-04:00",
            source: "yfinance",
            interval: "1m",
          }
        : null,
    intraday_error: null,
    analysis: {
      industry_overview: ["產業偏多"],
      company_overview: ["基本面穩定"],
      volume_price_analysis: "量價同步",
      scenarios: [{ name: "震盪整理", entry_range: "108-110", stop_loss: 104, target: "115" }],
      conclusion: "偏多但不追高。",
    },
  };
}

const twPayload = buildPayload("tw", "2330");
const usPayload = buildPayload("us", "AAPL");

vi.mock("@/lib/hooks/useDashboard", () => ({
  useDashboard: (symbol: string | null, market: Market) => {
    if (mockLoading) {
      return {
        data: undefined,
        error: undefined,
        isLoading: true,
        mutate: mockMutate,
      };
    }
    if (!symbol) {
      return {
        data: undefined,
        error: undefined,
        isLoading: false,
        mutate: mockMutate,
      };
    }
    return {
      data: market === "tw" ? twPayload : usPayload,
      error: undefined,
      isLoading: false,
      mutate: mockMutate,
    };
  },
}));

vi.mock("@/components/dashboard/candlestick-chart", () => ({
  CandlestickChart: () => <div data-testid="candlestick-chart" />,
}));

vi.mock("@/components/market-switcher", () => ({
  MarketSwitcher: ({ onChange }: { onChange: (next: Market) => void }) => (
    <div>
      <button type="button" onClick={() => onChange("tw")}>
        TW
      </button>
      <button type="button" onClick={() => onChange("us")}>
        US
      </button>
    </div>
  ),
}));

vi.mock("@/components/stock-selector", () => ({
  StockSelector: ({
    value,
    onInputChange,
  }: {
    value: string;
    onInputChange: (next: string) => void;
  }) => (
    <input
      aria-label="stock-input"
      value={value}
      onChange={(event) => onInputChange(event.target.value)}
    />
  ),
}));

describe("P11 placeholders", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockLoading = false;
  });

  it("renders six P11 placeholder panels for TW market", () => {
    render(<DashboardPageClient />);

    const panelIds = [
      "p11-panel-pe-ratio",
      "p11-panel-monthly-revenue",
      "p11-panel-historical-dividend-pe",
      "p11-panel-institutional-cost",
      "p11-panel-event-calendar",
      "p11-panel-retail-sentiment",
    ];
    panelIds.forEach((id) => {
      const panel = screen.getByTestId(id);
      expect(panel).toHaveClass("border-dashed");
    });

    expect(screen.getByText("本益比")).toBeInTheDocument();
    expect(screen.getByText("月營收")).toBeInTheDocument();
    expect(screen.getByText("歷史除息本益比")).toBeInTheDocument();
    expect(screen.getByText("法人持股成本")).toBeInTheDocument();
    expect(screen.getByText("事件行事曆")).toBeInTheDocument();
    expect(screen.getByText("散戶多空比")).toBeInTheDocument();
  });

  it("renders tooltip trigger for every P11 panel title", () => {
    render(<DashboardPageClient />);

    Object.values(P11_TOOLTIP_TEXT).forEach((tooltipText) => {
      expect(screen.getByLabelText(tooltipText)).toBeInTheDocument();
    });
  });

  it("renders same-industry button without triggering API call in 11-A", () => {
    render(<DashboardPageClient />);

    fireEvent.click(screen.getByRole("button", { name: "同產業 ->" }));
    expect(mockMutate).not.toHaveBeenCalled();
  });

  it("does not render P11 placeholders in US market", () => {
    render(<DashboardPageClient />);

    fireEvent.click(screen.getByRole("button", { name: "US" }));
    fireEvent.change(screen.getByLabelText("stock-input"), {
      target: { value: "AAPL" },
    });
    fireEvent.click(screen.getByRole("button", { name: "分析" }));

    expect(screen.queryByTestId("p11-panel-pe-ratio")).not.toBeInTheDocument();
    expect(screen.queryByTestId("p11-panel-monthly-revenue")).not.toBeInTheDocument();
    expect(screen.getByText("技術分析總覽")).toBeInTheDocument();
  });

  it("uses 300px chart loading skeleton height", () => {
    mockLoading = true;
    render(<DashboardPageClient />);

    expect(screen.getByTestId("dashboard-chart-skeleton")).toHaveClass("h-[300px]");
  });

  it("renders compact inline rows in chip panel", () => {
    render(<DashboardPageClient />);

    expect(screen.getByTestId("chip-bid-ask-inline")).toHaveTextContent("買方 53.00% / 賣方 47.00%");
    expect(screen.getByTestId("chip-margin-inline")).toHaveTextContent("+300 張");
    expect(screen.getByTestId("chip-short-inline")).toHaveTextContent("-120 張");
  });

  it("formats TW levels by tick size (high price no decimals)", () => {
    render(<DashboardPageClient />);

    expect(screen.getByText("533 / 30.43")).toBeInTheDocument();
    expect(screen.getByText("28.42 / 23.07")).toBeInTheDocument();
  });
});
