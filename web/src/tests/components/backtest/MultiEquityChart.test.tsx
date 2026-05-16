import { act, render, screen, within } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { BacktestBatchSummary } from "@/components/backtest/batch-types";

let addSeriesCalls: Array<{ color?: string }> = [];
let createdSeries: Array<{ setData: ReturnType<typeof vi.fn> }> = [];
let crosshairHandler: ((param: any) => void) | null = null;
const mockSetData = vi.fn();
const mockChart = {
  addSeries: vi.fn((_: unknown, opts: { color?: string }) => {
    addSeriesCalls.push(opts);
    const series = { setData: mockSetData };
    createdSeries.push(series);
    return series;
  }),
  removeSeries: vi.fn(),
  applyOptions: vi.fn(),
  timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
  subscribeCrosshairMove: vi.fn((handler: (param: any) => void) => {
    crosshairHandler = handler;
  }),
  unsubscribeCrosshairMove: vi.fn(),
  remove: vi.fn(),
};

vi.mock("lightweight-charts", () => ({
  ColorType: { Solid: "solid" },
  LineSeries: "LineSeries",
  createChart: vi.fn(() => mockChart),
}));

global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
})) as unknown as typeof ResizeObserver;

import { MultiEquityChart, STRATEGY_COLORS } from "@/components/backtest/MultiEquityChart";

const SUMMARIES: BacktestBatchSummary[] = [
  {
    preset_index: 0,
    preset_name: "MA20_MA60",
    strategy_type: "moving_average_cross",
    strategy_params: {},
    total_return: 0.1,
    annual_return: 0.02,
    max_drawdown: 0.1,
    sharpe_ratio: 0.8,
    win_rate: 0.5,
    profit_factor: 1.2,
    total_trades: 10,
    error: null,
    detail: {
      symbol: "2330",
      market: "tw",
      currency: "TWD",
      engine: "vectorized",
      strategy_type: "moving_average_cross",
      strategy_params: {},
      metrics: null,
      equity_curve: [
        { date: "2020-01-01", value: 1000000 },
        { date: "2020-01-02", value: 1010000 },
      ],
      trades: [],
      signals: [],
      dca_warning: null,
    },
  },
  {
    preset_index: 1,
    preset_name: "RSI_14",
    strategy_type: "rsi",
    strategy_params: {},
    total_return: 0.2,
    annual_return: 0.05,
    max_drawdown: 0.12,
    sharpe_ratio: 1.1,
    win_rate: 0.6,
    profit_factor: 1.7,
    total_trades: 8,
    error: null,
    detail: {
      symbol: "2330",
      market: "tw",
      currency: "TWD",
      engine: "vectorized",
      strategy_type: "rsi",
      strategy_params: {},
      metrics: null,
      equity_curve: [
        { date: "2020-01-01", value: 1000000 },
        { date: "2020-01-02", value: 1020000 },
      ],
      trades: [],
      signals: [],
      dca_warning: null,
    },
  },
];

describe("MultiEquityChart", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    addSeriesCalls = [];
    createdSeries = [];
    crosshairHandler = null;
  });

  it("renders legend items for each successful summary", () => {
    render(<MultiEquityChart summaries={SUMMARIES} />);
    expect(screen.getAllByTestId("multi-equity-legend-item")).toHaveLength(2);
  });

  it("uses palette colors in series order", () => {
    render(<MultiEquityChart summaries={SUMMARIES} />);
    expect(addSeriesCalls[0]?.color).toBe(STRATEGY_COLORS[0]);
    expect(addSeriesCalls[1]?.color).toBe(STRATEGY_COLORS[1]);
  });

  it("renders empty state when no usable series", () => {
    const onlyError = [{ ...SUMMARIES[0], error: "failed", detail: null }];
    render(<MultiEquityChart summaries={onlyError} />);
    expect(screen.getByTestId("multi-equity-chart-empty")).toBeInTheDocument();
  });

  it("shows crosshair tooltip with all strategy values on hovered date", () => {
    render(<MultiEquityChart summaries={SUMMARIES} />);
    expect(crosshairHandler).toBeTruthy();
    expect(createdSeries).toHaveLength(2);

    act(() => {
      crosshairHandler?.({
        point: { x: 100, y: 80 },
        time: "2020-01-02",
        seriesData: new Map([
          [createdSeries[0], { value: 1010000 }],
          [createdSeries[1], { value: 1020000 }],
        ]),
      });
    });

    const tooltip = screen.getByTestId("multi-equity-tooltip");
    expect(tooltip).toBeInTheDocument();
    expect(within(tooltip).getByText("MA20_MA60")).toBeInTheDocument();
    expect(within(tooltip).getByText("RSI_14")).toBeInTheDocument();
    expect(within(tooltip).getByText("1,010,000")).toBeInTheDocument();
    expect(within(tooltip).getByText("1,020,000")).toBeInTheDocument();
  });
});
