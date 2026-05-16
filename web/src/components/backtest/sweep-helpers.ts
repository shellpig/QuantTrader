import type { Market } from "@/types/market";
import { SWEEP_DEFAULTS, SWEEP_PARAM_SPECS, SWEEP_PARAM_TYPES } from "./sweep-constants";
import type { SweepStrategyType } from "./sweep-types";

export const SWEEP_STRATEGY_LABELS: Record<SweepStrategyType, string> = {
  moving_average_cross: "雙均線交叉",
  rsi: "RSI",
  kd_cross: "KD 交叉",
  macd_cross: "MACD 交叉",
  bollinger_band: "布林通道",
  bias: "乖離率",
  donchian_breakout: "Donchian 突破",
};

export const SWEEP_PARAM_LABELS: Record<string, string> = {
  short_window: "短均線",
  long_window: "長均線",
  period: "週期",
  oversold: "超賣",
  overbought: "超買",
  k_period: "K 週期",
  d_period: "D 週期",
  smooth_k: "平滑 K",
  fast: "快線",
  slow: "慢線",
  signal: "訊號線",
  std_dev: "標準差",
  ma_period: "均線週期",
  buy_bias: "買進乖離",
  sell_bias: "賣出乖離",
  entry_period: "進場週期",
  exit_period: "出場週期",
};

export interface SweepAnalysis {
  paramKeys: string[];
  paramCandidates: Record<string, number[]>;
  totalCombos: number;
  validCombos: number;
  hasParseError: boolean;
}

export interface SweepStartPayload {
  market: Market;
  symbol: string;
  start_date: string;
  end_date: string;
  strategy_type: SweepStrategyType;
  param_candidates: Record<string, number[]>;
  initial_capital: number;
  total_combos: number;
  valid_combos: number;
  max_combos_limit: number;
}

export function createDefaultParamInputs(strategyType: SweepStrategyType): Record<string, string> {
  return { ...SWEEP_DEFAULTS[strategyType] };
}

export function parseCommaNumberList(
  raw: string,
  expectedType: "int" | "float" = "float",
): number[] {
  const parts = raw
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  if (parts.length === 0) return [];
  const values: number[] = [];
  for (const part of parts) {
    const num = Number(part);
    if (!Number.isFinite(num)) return [];
    if (expectedType === "int" && !Number.isInteger(num)) return [];
    values.push(num);
  }
  return Array.from(new Set(values)).sort((a, b) => a - b).map(normalizeSweepNumber);
}

export function normalizeSweepNumber(value: number): number {
  return Number.isInteger(value) ? Math.trunc(value) : value;
}

export function analyzeSweepInputs(
  strategyType: SweepStrategyType,
  paramInputs: Record<string, string>,
): SweepAnalysis {
  const paramKeys = SWEEP_PARAM_SPECS[strategyType];
  const paramCandidates: Record<string, number[]> = {};
  let hasParseError = false;
  for (const key of paramKeys) {
    const expectedType = SWEEP_PARAM_TYPES[key] ?? "float";
    const parsed = parseCommaNumberList(paramInputs[key] ?? "", expectedType);
    if (parsed.length === 0) {
      hasParseError = true;
      continue;
    }
    paramCandidates[key] = parsed;
  }

  if (hasParseError) {
    return {
      paramKeys,
      paramCandidates,
      totalCombos: 0,
      validCombos: 0,
      hasParseError: true,
    };
  }

  const combos = buildParamGrid(paramKeys, paramCandidates);
  let validCombos = 0;
  for (const combo of combos) {
    if (isValidSweepParams(strategyType, combo)) {
      validCombos += 1;
    }
  }
  return {
    paramKeys,
    paramCandidates,
    totalCombos: combos.length,
    validCombos,
    hasParseError: false,
  };
}

export function buildParamGrid(
  keys: string[],
  paramCandidates: Record<string, number[]>,
): Record<string, number>[] {
  if (keys.length === 0) return [];
  let combos: Record<string, number>[] = [{}];
  for (const key of keys) {
    const values = paramCandidates[key] ?? [];
    const next: Record<string, number>[] = [];
    for (const base of combos) {
      for (const value of values) {
        next.push({ ...base, [key]: value });
      }
    }
    combos = next;
  }
  return combos;
}

export function isValidSweepParams(
  strategyType: SweepStrategyType,
  params: Record<string, number>,
): boolean {
  if (strategyType === "moving_average_cross") {
    const shortWindow = toInt(params.short_window);
    const longWindow = toInt(params.long_window);
    return shortWindow > 0 && longWindow > 0 && shortWindow < longWindow;
  }
  if (strategyType === "rsi") {
    const period = toInt(params.period);
    const oversold = toNum(params.oversold);
    const overbought = toNum(params.overbought);
    return period > 0 && oversold >= 0 && overbought <= 100 && oversold < overbought;
  }
  if (strategyType === "kd_cross") {
    return toInt(params.k_period) > 0 && toInt(params.d_period) > 0 && toInt(params.smooth_k) > 0;
  }
  if (strategyType === "macd_cross") {
    const fast = toInt(params.fast);
    const slow = toInt(params.slow);
    const signal = toInt(params.signal);
    return fast > 0 && slow > 0 && signal > 0 && fast < slow;
  }
  if (strategyType === "bollinger_band") {
    return toInt(params.period) > 0 && toNum(params.std_dev) > 0;
  }
  if (strategyType === "bias") {
    const maPeriod = toInt(params.ma_period);
    const buyBias = toNum(params.buy_bias);
    const sellBias = toNum(params.sell_bias);
    return maPeriod > 0 && buyBias < sellBias;
  }
  if (strategyType === "donchian_breakout") {
    return toInt(params.entry_period) > 0 && toInt(params.exit_period) > 0;
  }
  return false;
}

function toNum(value: unknown): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

function toInt(value: unknown): number {
  return Math.trunc(toNum(value));
}
