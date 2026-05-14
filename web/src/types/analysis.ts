// Analysis / Dashboard types (Phase 10-B)
// Mirrors Python dataclasses in src/services/dashboard_service.py

import type { Market } from "./market";

export interface TechnicalSummary {
  trend: string;
  trend_strength: string;
  ma5: number | null;
  ma20: number | null;
  ma60: number | null;
  rsi: number | null;
  rsi_signal: string;
  macd: number | null;
  macd_signal: number | null;
  macd_histogram: number | null;
  macd_trend: string;
  kd_k: number | null;
  kd_d: number | null;
  kd_signal: string;
  bb_upper: number | null;
  bb_lower: number | null;
  bb_signal: string;
  support: number | null;
  resistance: number | null;
  volume_ma20: number | null;
  volume_ratio: number | null;
  price_change_1d: number | null;
  price_change_5d: number | null;
  price_change_20d: number | null;
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
  date: string;       // "YYYY-MM-DD" for daily
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
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
}

export interface DashboardPayloadResponse {
  symbol: string;
  market: Market;
  daily_bars: OhlcvBar[];
  technical: TechnicalSummary;
  candle_patterns: CandlePattern[];
  chart_patterns: ChartPatternResult[];
  multi_timeframe: MultiTimeframeAnalysis;
  ai_enabled: boolean;
  quote: RealtimeQuote | null;
  chip: ChipSummary | null;
  chip_error: string | null;
  intraday_snapshot: USIntradaySnapshot | null;
  intraday_error: string | null;
  subject_name: string;
  analysis_time: string;
}

export interface ApiError {
  error: {
    code: string;
    message: string;
  };
}
