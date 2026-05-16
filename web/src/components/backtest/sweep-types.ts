import type { Market } from "@/types/market";

export type SweepStrategyType =
  | "moving_average_cross"
  | "rsi"
  | "kd_cross"
  | "macd_cross"
  | "bollinger_band"
  | "bias"
  | "donchian_breakout";

export interface SweepResultRow {
  params: Record<string, number>;
  total_return: number | null;
  annual_return: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  total_trades: number;
  error: string | null;
  sample_warning: boolean;
}

export interface BacktestSweepResult {
  symbol: string;
  market: Market;
  currency: "TWD" | "USD";
  strategy_type: SweepStrategyType;
  start_date: string;
  end_date: string;
  total_combos: number;
  valid_combos: number;
  max_combos_limit: number;
  results: SweepResultRow[];
}
