// Backtest types (Phase 10-B)

import type { Market } from "./market";

export type EngineType = "vectorized" | "event_driven";

export interface StrategyPreset {
  name: string;
  type: string;
  params: Record<string, number | string | boolean>;
}

export interface BacktestMetrics {
  total_trades: number;
  total_return: number;
  annual_return: number;
  max_drawdown: number;
  sharpe_ratio: number;
  win_rate: number;
  profit_factor: number;
}

export interface TradeLeg {
  entry_date: string;
  entry_price: number;
  exit_date: string | null;
  exit_price: number | null;
  quantity: number;
  pnl: number | null;
}

export interface BacktestJobResult {
  symbol: string;
  market: Market;
  strategy_type: string;
  strategy_params: Record<string, unknown>;
  currency: string;
  engine: string;
  metrics: BacktestMetrics | null;
  trades: TradeLeg[];
  error: string | null;
}

export interface JobStatus {
  job_id: string;
  type: string;
  status: "pending" | "running" | "complete" | "error" | "cancelled";
  progress: number;
  message: string;
  created_at: string;
}
