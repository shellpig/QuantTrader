import type { SweepStrategyType } from "./sweep-types";

export const MAX_SWEEP_COMBOS = 200;

export const SWEEP_PARAM_SPECS: Record<SweepStrategyType, string[]> = {
  moving_average_cross: ["short_window", "long_window"],
  rsi: ["period", "oversold", "overbought"],
  kd_cross: ["k_period", "d_period", "smooth_k"],
  macd_cross: ["fast", "slow", "signal"],
  bollinger_band: ["period", "std_dev"],
  bias: ["ma_period", "buy_bias", "sell_bias"],
  donchian_breakout: ["entry_period", "exit_period"],
};

export const SWEEP_PARAM_TYPES: Record<string, "int" | "float"> = {
  short_window: "int",
  long_window: "int",
  period: "int",
  oversold: "float",
  overbought: "float",
  k_period: "int",
  d_period: "int",
  smooth_k: "int",
  fast: "int",
  slow: "int",
  signal: "int",
  std_dev: "float",
  ma_period: "int",
  buy_bias: "float",
  sell_bias: "float",
  entry_period: "int",
  exit_period: "int",
};

export const SWEEP_DEFAULTS: Record<SweepStrategyType, Record<string, string>> = {
  moving_average_cross: { short_window: "5,10,20", long_window: "40,60,120" },
  rsi: { period: "7,14,21", oversold: "20,30", overbought: "70,80" },
  kd_cross: { k_period: "9,14", d_period: "3,5", smooth_k: "3,5" },
  macd_cross: { fast: "8,12", slow: "20,26", signal: "7,9" },
  bollinger_band: { period: "10,20,30", std_dev: "1.5,2.0,2.5" },
  bias: { ma_period: "10,20,30", buy_bias: "-15,-10,-5", sell_bias: "5,10,15" },
  donchian_breakout: { entry_period: "10,20,55", exit_period: "5,10,20" },
};
