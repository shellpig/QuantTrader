"use client";

import { useMemo } from "react";
import { MarketSwitcher } from "@/components/market-switcher";
import { StockSelector } from "@/components/stock-selector";
import type { Market } from "@/types/market";
import { MAX_SWEEP_COMBOS } from "./sweep-constants";
import type { SweepStrategyType } from "./sweep-types";
import type { SweepStartPayload } from "./sweep-helpers";
import {
  SWEEP_PARAM_LABELS,
  SWEEP_STRATEGY_LABELS,
  analyzeSweepInputs,
} from "./sweep-helpers";
import { DateRangePicker } from "./DateRangePicker";

interface ParamGridFormProps {
  market: Market;
  symbol: string;
  startDate: string;
  endDate: string;
  strategyType: SweepStrategyType;
  paramInputs: Record<string, string>;
  initialCapital: number;
  disabled?: boolean;
  onMarketChange: (market: Market) => void;
  onSymbolChange: (symbol: string) => void;
  onStartDateChange: (date: string) => void;
  onEndDateChange: (date: string) => void;
  onStrategyTypeChange: (strategy: SweepStrategyType) => void;
  onParamInputChange: (key: string, value: string) => void;
  onInitialCapitalChange: (value: number) => void;
  onSubmit: (payload: SweepStartPayload) => void;
}

export function ParamGridForm({
  market,
  symbol,
  startDate,
  endDate,
  strategyType,
  paramInputs,
  initialCapital,
  disabled = false,
  onMarketChange,
  onSymbolChange,
  onStartDateChange,
  onEndDateChange,
  onStrategyTypeChange,
  onParamInputChange,
  onInitialCapitalChange,
  onSubmit,
}: ParamGridFormProps) {
  const analysis = useMemo(
    () => analyzeSweepInputs(strategyType, paramInputs),
    [strategyType, paramInputs],
  );

  const canSubmit =
    !disabled &&
    Boolean(symbol) &&
    !analysis.hasParseError &&
    analysis.validCombos > 0 &&
    analysis.validCombos <= MAX_SWEEP_COMBOS;

  function handleSubmit() {
    if (!canSubmit) return;
    onSubmit({
      market,
      symbol,
      start_date: startDate,
      end_date: endDate,
      strategy_type: strategyType,
      param_candidates: analysis.paramCandidates,
      initial_capital: initialCapital,
      total_combos: analysis.totalCombos,
      valid_combos: analysis.validCombos,
      max_combos_limit: MAX_SWEEP_COMBOS,
    });
  }

  return (
    <div data-testid="sweep-form" className="space-y-3 rounded-lg border border-slate-700 bg-slate-800/40 p-4">
      <div className="flex flex-wrap items-end gap-3">
        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">市場</label>
          <MarketSwitcher value={market} onChange={onMarketChange} />
        </div>

        <div className="flex min-w-[240px] flex-col gap-1">
          <label className="text-xs text-slate-400">股票代碼</label>
          <StockSelector market={market} value={symbol} onChange={onSymbolChange} />
        </div>

        <DateRangePicker
          startDate={startDate}
          endDate={endDate}
          onStartChange={onStartDateChange}
          onEndChange={onEndDateChange}
          disabled={disabled}
        />

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">策略類型</label>
          <select
            data-testid="sweep-strategy-type"
            value={strategyType}
            onChange={(e) => onStrategyTypeChange(e.target.value as SweepStrategyType)}
            disabled={disabled}
            className="rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 disabled:opacity-50"
          >
            {Object.entries(SWEEP_STRATEGY_LABELS).map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1">
          <label className="text-xs text-slate-400">初始資金</label>
          <input
            type="number"
            data-testid="sweep-initial-capital"
            value={initialCapital}
            onChange={(e) => onInitialCapitalChange(Number(e.target.value))}
            disabled={disabled}
            min={1}
            step={10000}
            className="w-32 rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 disabled:opacity-50"
          />
        </div>

        <button
          type="button"
          data-testid="start-sweep-btn"
          disabled={!canSubmit}
          onClick={handleSubmit}
          className="rounded bg-sky-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-sky-500 disabled:opacity-50"
        >
          開始掃描
        </button>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {analysis.paramKeys.map((key) => (
          <div key={key} className="flex flex-col gap-1">
            <label className="text-xs text-slate-400">{SWEEP_PARAM_LABELS[key] ?? key}</label>
            <input
              data-testid={`param-input-${key}`}
              value={paramInputs[key] ?? ""}
              onChange={(e) => onParamInputChange(key, e.target.value)}
              disabled={disabled}
              placeholder="例如 5,10,20"
              className="rounded border border-slate-700 bg-slate-800 px-2 py-1.5 text-sm text-slate-100 placeholder:text-slate-500 disabled:opacity-50"
            />
          </div>
        ))}
      </div>

      <div data-testid="sweep-combo-summary" className="text-xs text-slate-300">
        總組合數 {analysis.totalCombos} / 合法組合數 {analysis.validCombos} / 上限 {MAX_SWEEP_COMBOS}
      </div>

      {analysis.hasParseError && (
        <p data-testid="sweep-parse-error" className="text-xs text-amber-300">
          參數格式錯誤，請用逗號分隔數字（例如 5,10,20）。
        </p>
      )}

      {!analysis.hasParseError && analysis.validCombos > MAX_SWEEP_COMBOS && (
        <p data-testid="sweep-over-limit" className="text-xs text-amber-300">
          合法組合數 {analysis.validCombos} 超過上限 {MAX_SWEEP_COMBOS}，請縮小參數範圍。
        </p>
      )}
    </div>
  );
}
