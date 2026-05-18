// Analysis / Dashboard types (Phase 10-D)
// Synced with docs/mock_dashboard_payload.json and backend dataclasses.

import type { Market } from "./market";

export interface PriceLevel {
  value: number;
  label: string;
  kind: string;
}

export interface TechnicalScoreComponents {
  ma: number;
  kd: number;
  volume_price: number;
  breakout: number;
}

export interface TechnicalSummary {
  trend_direction: string;
  ma_status: string;
  kd_status: string;
  macd_status: string;
  volume_status: string;
  volume_price_relation: string;
  short_term_score: number;
  short_term_label: string;
  short_term_components: TechnicalScoreComponents;
  resistance_levels: PriceLevel[];
  support_levels: PriceLevel[];
  volume_price_divergence: string;
  ma_bias: string;
  chip_behavior: string;
  operation_observation: string;
}

export interface CandlePattern {
  name: string;
  detected: boolean;
  description: string;
}

export interface ChartPatternResult {
  pattern_type: string;
  formed: boolean;
  description: string;
  key_points: [string, number][];
}

export interface TimeframeTrend {
  timeframe: string;
  trend_direction: string;
  strength: string;
}

export interface MultiTimeframeAnalysis {
  daily: TimeframeTrend;
  weekly: TimeframeTrend;
  monthly: TimeframeTrend;
}

export interface ChipSummary {
  foreign_net_n_days: number;
  trust_net_n_days: number;
  dealer_net_n_days: number;
  foreign_label: string;
  trust_label: string;
  dealer_label: string;
  chip_concentration: string;
  chip_trend: string;
  chip_description: string;
  margin_balance_change: number;
  short_balance_change: number;
}

export interface OhlcvBar {
  date: string; // ISO 8601 with timezone, e.g. "2025-11-11T00:00:00+08:00"
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  symbol: string;
}

export interface USIntradaySnapshot {
  symbol: string;
  price: number;
  previous_raw_close: number;
  change: number;
  change_pct: number;
  volume: number;
  timestamp: string;   // ISO 8601, America/New_York
  source: string;
  interval: string;
}

export interface RealtimeQuote {
  symbol: string;
  name: string;
  price: number;
  change: number;
  change_pct: number;
  open: number;
  high: number;
  low: number;
  yesterday_close: number;
  volume: number;
  timestamp: string;
  trade_date: string | null;
  best_bid: number[];
  best_ask: number[];
  best_bid_vol: number[];
  best_ask_vol: number[];
  is_market_open: boolean;
  is_estimated_price: boolean;
  price_label: string;
  estimated_price: number | null;
}

export interface BidAskStructure {
  total_bid_vol: number;
  total_ask_vol: number;
  bid_ratio: number;
  ask_ratio: number;
  label: string;
}

export interface TradingScenario {
  name: string;
  entry_range: string;
  stop_loss: number;
  target: string;
}

export interface DashboardAnalysis {
  industry_overview: string[];
  company_overview: string[];
  volume_price_analysis: string;
  scenarios: TradingScenario[];
  conclusion: string;
}

export interface ChipRecentRow {
  日期: string;
  外資: number;
  投信: number;
  自營商: number;
}

export interface DashboardPayloadResponse {
  symbol: string;
  market: Market;
  subject_name: string;
  analysis_time: string;
  ai_enabled: boolean;
  daily_df: OhlcvBar[];
  technical: TechnicalSummary;
  candle_patterns: CandlePattern[];
  chart_patterns: ChartPatternResult[];
  multi_timeframe: MultiTimeframeAnalysis;
  quote: RealtimeQuote | null;
  bid_ask: BidAskStructure | null;
  chip: ChipSummary | null;
  chip_recent_df: ChipRecentRow[];
  chip_error: string | null;
  intraday_df: OhlcvBar[];
  intraday_snapshot: USIntradaySnapshot | null;
  intraday_error: string | null;
  analysis: DashboardAnalysis | null;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}

export interface P11ValuationResponse {
  symbol: string;
  market: Market;
  date: string | null;
  per: number | null;
  pbr: number | null;
  dividend_yield: number | null;
  industry: string | null;
}

export interface P11MonthlyRevenueItem {
  date: string;
  revenue: number | null;
  revenue_year: number;
  revenue_month: number;
  yoy: number | null;
  mom: number | null;
}

export interface P11MonthlyRevenueResponse {
  symbol: string;
  market: Market;
  latest_month: string | null;
  latest_revenue: number | null;
  items: P11MonthlyRevenueItem[];
}

export interface P11DividendHistoryItem {
  date: string;
  cash_dividend: number | null;
  stock_dividend?: number | null;
  ttm_pe: number | null;
  price_date?: string | null;
}

export interface P11DividendHistoryResponse {
  symbol: string;
  market: Market;
  items: P11DividendHistoryItem[];
}

export interface P11IndustryPerItem {
  symbol: string;
  name: string;
  date: string | null;
  per: number | null;
  pbr: number | null;
  dividend_yield: number | null;
  is_current: boolean;
}

export interface P11IndustryPerResponse {
  symbol: string;
  market: Market;
  industry: string | null;
  median: number | null;
  mean: number | null;
  count: number;
  items: P11IndustryPerItem[];
  cached_at: string | null;
}

export interface P11InstitutionalCostEntry {
  cost: number | null;
  pnl: number | null;
}

export interface P11InstitutionalCostResponse {
  symbol: string;
  market: Market;
  days: number;
  current_price: number | null;
  foreign: P11InstitutionalCostEntry;
  trust: P11InstitutionalCostEntry;
  dealer: P11InstitutionalCostEntry;
}

export interface P11EventCalendarEntry {
  date: string;
  meeting_type?: string | null;
  source?: string | null;
  is_manual?: boolean;
  cash_dividend?: number | null;
  stock_dividend?: number | null;
  days_until?: number | null;
  is_estimated?: boolean;
}

export interface P11EventCalendarResponse {
  symbol: string;
  market: Market;
  next_ex_dividend: P11EventCalendarEntry | null;
  last_ex_dividend: P11EventCalendarEntry | null;
  next_shareholder_meeting: P11EventCalendarEntry | null;
  last_shareholder_meeting: P11EventCalendarEntry | null;
  missing_shareholder_meeting: boolean;
  is_etf?: boolean;
}
