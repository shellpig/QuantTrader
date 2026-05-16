import type { Market } from "@/types/market";

export interface BatchRunDetail {
  symbol: string;
  market: Market;
  currency: string;
  engine: string;
  strategy_type: string;
  strategy_params: Record<string, number | string | boolean>;
  metrics: {
    total_trades: number | null;
    total_return: number | null;
    annual_return: number | null;
    max_drawdown: number | null;
    max_drawdown_start?: string | null;
    max_drawdown_end?: string | null;
    sharpe_ratio: number | null;
    win_rate: number | null;
    profit_factor?: number | null;
  } | null;
  equity_curve: Array<{ date: string; value: number }>;
  trades: Array<{
    entry_date: string;
    exit_date: string;
    side: string;
    entry_price: number;
    exit_price: number;
    shares: number;
    pnl: number;
    return_pct: number;
  }>;
  signals: Array<{ date: string; side: "buy" | "sell"; price: number }>;
  dca_warning: string | null;
}

export interface BacktestBatchSummary {
  preset_index: number;
  preset_name: string;
  strategy_type: string;
  strategy_params: Record<string, number | string | boolean>;
  total_return: number | null;
  annual_return: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  total_trades: number;
  error: string | null;
  detail: BatchRunDetail | null;
}

export interface BacktestBatchResult {
  symbol: string;
  market: Market;
  currency: string;
  engine: string;
  start_date: string;
  end_date: string;
  total_presets: number;
  completed_presets: number;
  success_count: number;
  failed_count: number;
  price_data: Array<{
    date: string;
    open: number;
    high: number;
    low: number;
    close: number;
    volume: number;
  }>;
  summaries: BacktestBatchSummary[];
}

