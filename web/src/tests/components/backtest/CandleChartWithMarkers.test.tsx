// Tests for CandleChartWithMarkers component (Phase 10-E-1)
// Verifies markers, MA overlays, and market colour conventions.
// lightweight-charts is mocked — tests assert what data/options are passed to the library.

import { render } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

// --------------------------------------------------------------------------
// Tracking state (closures into mock implementations)
// --------------------------------------------------------------------------

type MarkerArg = { time: string; color: string; position: string; shape: string; text: string };
let lastMarkersArg: MarkerArg[] = [];
let addSeriesCalls: Array<[unknown, Record<string, string>]> = [];

// --------------------------------------------------------------------------
// lightweight-charts mock
// --------------------------------------------------------------------------

const mockSetData = vi.fn();
const mockRemoveSeries = vi.fn();
const mockSetVisibleLogicalRange = vi.fn();
const mockSetMarkers = vi.fn();

const mockChart = {
  addSeries: vi.fn((SeriesClass: unknown, opts: Record<string, string>) => {
    addSeriesCalls.push([SeriesClass, opts]);
    return { setData: mockSetData, applyOptions: vi.fn() };
  }),
  removeSeries: mockRemoveSeries,
  applyOptions: vi.fn(),
  timeScale: vi.fn(() => ({ setVisibleLogicalRange: mockSetVisibleLogicalRange })),
  remove: vi.fn(),
};

vi.mock("lightweight-charts", () => ({
  CandlestickSeries: "CandlestickSeries",
  LineSeries: "LineSeries",
  ColorType: { Solid: "Solid" },
  createChart: vi.fn(() => mockChart),
  createSeriesMarkers: vi.fn((_: unknown, markers: MarkerArg[]) => {
    lastMarkersArg = markers;
    return { setMarkers: mockSetMarkers };
  }),
}));

// ResizeObserver polyfill (not in jsdom)
global.ResizeObserver = vi.fn(() => ({
  observe: vi.fn(),
  disconnect: vi.fn(),
})) as unknown as typeof ResizeObserver;

// --------------------------------------------------------------------------
// Import component AFTER mock setup
// --------------------------------------------------------------------------

import { CandleChartWithMarkers } from "@/components/backtest/CandleChartWithMarkers";

// --------------------------------------------------------------------------
// Fixtures
// --------------------------------------------------------------------------

const THREE_BARS = [
  { date: "2020-03-15", open: 280, high: 290, low: 275, close: 285, volume: 1000 },
  { date: "2020-05-20", open: 305, high: 315, low: 300, close: 310, volume: 2000 },
  { date: "2020-07-01", open: 320, high: 330, low: 315, close: 325, volume: 1500 },
];

// --------------------------------------------------------------------------
// Tests
// --------------------------------------------------------------------------

describe("CandleChartWithMarkers", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastMarkersArg = [];
    addSeriesCalls = [];
    // Restore addSeries impl (clearAllMocks resets mock.calls but not impl; reassign for safety)
    mockChart.addSeries.mockImplementation((SeriesClass: unknown, opts: Record<string, string>) => {
      addSeriesCalls.push([SeriesClass, opts]);
      return { setData: mockSetData, applyOptions: vi.fn() };
    });
    mockChart.timeScale.mockReturnValue({ setVisibleLogicalRange: mockSetVisibleLogicalRange });
  });

  // 1. Marker count matches signal count
  it("creates one marker per signal that matches a price bar date", () => {
    const signals = [
      { date: "2020-03-15", side: "buy" as const, price: 280 },
      { date: "2020-05-20", side: "sell" as const, price: 310 },
    ];
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={signals} market="tw" />);
    expect(lastMarkersArg).toHaveLength(2);
  });

  // 2. Signals whose date is absent from priceData are filtered out
  it("filters out signals not present in priceData dates", () => {
    const signals = [
      { date: "2020-03-15", side: "buy" as const, price: 280 },
      { date: "1999-12-31", side: "sell" as const, price: 100 }, // no matching bar
    ];
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={signals} market="tw" />);
    expect(lastMarkersArg).toHaveLength(1);
  });

  // 3. Empty signals → no markers
  it("creates no markers when signals array is empty", () => {
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={[]} market="tw" />);
    expect(lastMarkersArg).toHaveLength(0);
  });

  // 4. 台股: buy → red (漲色), sell → green (跌色)
  it("uses red for buy and green for sell on TW market (台股紅漲綠跌)", () => {
    const signals = [
      { date: "2020-03-15", side: "buy" as const, price: 280 },
      { date: "2020-05-20", side: "sell" as const, price: 310 },
    ];
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={signals} market="tw" />);

    const buyMarker = lastMarkersArg.find((m) => m.text === "B");
    const sellMarker = lastMarkersArg.find((m) => m.text === "S");
    expect(buyMarker?.color).toBe("#ef4444");  // MARKET_UP_COLOR.tw
    expect(sellMarker?.color).toBe("#22c55e"); // MARKET_DOWN_COLOR.tw
  });

  // 5. 美股: buy → green (漲色), sell → red (跌色) — reverse of TW
  it("uses green for buy and red for sell on US market (美股綠漲紅跌)", () => {
    const signals = [
      { date: "2020-03-15", side: "buy" as const, price: 280 },
      { date: "2020-05-20", side: "sell" as const, price: 310 },
    ];
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={signals} market="us" />);

    const buyMarker = lastMarkersArg.find((m) => m.text === "B");
    const sellMarker = lastMarkersArg.find((m) => m.text === "S");
    expect(buyMarker?.color).toBe("#22c55e");  // MARKET_UP_COLOR.us
    expect(sellMarker?.color).toBe("#ef4444"); // MARKET_DOWN_COLOR.us
  });

  // 6. Marker positions: buy belowBar, sell aboveBar
  it("sets belowBar position for buy and aboveBar for sell", () => {
    const signals = [
      { date: "2020-03-15", side: "buy" as const, price: 280 },
      { date: "2020-05-20", side: "sell" as const, price: 310 },
    ];
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={signals} market="tw" />);

    const buyMarker = lastMarkersArg.find((m) => m.text === "B");
    const sellMarker = lastMarkersArg.find((m) => m.text === "S");
    expect(buyMarker?.position).toBe("belowBar");
    expect(sellMarker?.position).toBe("aboveBar");
  });

  // 7. No MA overlay → no LineSeries added
  it("adds no LineSeries when maOverlay is empty", () => {
    render(<CandleChartWithMarkers priceData={THREE_BARS} signals={[]} market="tw" maOverlay={[]} />);
    const lineCalls = addSeriesCalls.filter(([cls]) => cls === "LineSeries");
    expect(lineCalls).toHaveLength(0);
  });

  // 8. Two MA overlays → two LineSeries added
  it("adds one LineSeries per entry in maOverlay", () => {
    const maOverlay = [
      { name: "MA20", period: 20, color: "#60a5fa" },
      { name: "MA60", period: 60, color: "#f59e0b" },
    ];
    render(
      <CandleChartWithMarkers priceData={THREE_BARS} signals={[]} market="tw" maOverlay={maOverlay} />,
    );
    const lineCalls = addSeriesCalls.filter(([cls]) => cls === "LineSeries");
    expect(lineCalls).toHaveLength(2);
  });
});
