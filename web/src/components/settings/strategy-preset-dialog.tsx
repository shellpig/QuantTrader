"use client";

import { useState, useEffect } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import type { StrategyPreset } from "@/hooks/use-config";

const STRATEGY_TYPES = [
  { value: "moving_average_cross", label: "均線交叉" },
  { value: "rsi", label: "RSI 超買超賣" },
  { value: "kd_cross", label: "KD 交叉" },
  { value: "macd_cross", label: "MACD 交叉" },
  { value: "bollinger_band", label: "布林通道" },
  { value: "bias", label: "乖離率" },
  { value: "donchian_breakout", label: "突破策略" },
] as const;

type StrategyTypeValue = (typeof STRATEGY_TYPES)[number]["value"];

interface ParamSpec {
  key: string;
  label: string;
  defaultValue: number;
}

const PARAM_SPECS: Record<StrategyTypeValue, ParamSpec[]> = {
  moving_average_cross: [
    { key: "short_window", label: "短均線週期", defaultValue: 20 },
    { key: "long_window", label: "長均線週期", defaultValue: 60 },
  ],
  rsi: [
    { key: "period", label: "RSI 週期", defaultValue: 14 },
    { key: "oversold", label: "超賣門檻", defaultValue: 30 },
    { key: "overbought", label: "超買門檻", defaultValue: 70 },
  ],
  kd_cross: [
    { key: "k_period", label: "K 值回看期間", defaultValue: 9 },
    { key: "d_period", label: "D 值平滑期間", defaultValue: 3 },
    { key: "smooth_k", label: "K 值平滑期間", defaultValue: 3 },
  ],
  macd_cross: [
    { key: "fast", label: "快線 EMA 週期", defaultValue: 12 },
    { key: "slow", label: "慢線 EMA 週期", defaultValue: 26 },
    { key: "signal", label: "訊號線 EMA 週期", defaultValue: 9 },
  ],
  bollinger_band: [
    { key: "period", label: "中軌 SMA 週期", defaultValue: 20 },
    { key: "std_dev", label: "標準差倍數", defaultValue: 2.0 },
  ],
  bias: [
    { key: "ma_period", label: "均線週期", defaultValue: 20 },
    { key: "buy_bias", label: "買進乖離率門檻（%）", defaultValue: -10 },
    { key: "sell_bias", label: "賣出乖離率門檻（%）", defaultValue: 10 },
  ],
  donchian_breakout: [
    { key: "entry_period", label: "進場回看天數", defaultValue: 20 },
    { key: "exit_period", label: "出場回看天數", defaultValue: 10 },
  ],
};

function defaultParams(type: StrategyTypeValue): Record<string, number> {
  return Object.fromEntries(
    PARAM_SPECS[type].map((p) => [p.key, p.defaultValue]),
  );
}

interface StrategyPresetDialogProps {
  open: boolean;
  initialPreset: StrategyPreset | null;
  onClose: () => void;
  onSave: (preset: StrategyPreset, isNew: boolean) => void;
}

export function StrategyPresetDialog({
  open,
  initialPreset,
  onClose,
  onSave,
}: StrategyPresetDialogProps) {
  const isNew = initialPreset === null;
  const [name, setName] = useState("");
  const [type, setType] = useState<StrategyTypeValue>("moving_average_cross");
  const [params, setParams] = useState<Record<string, number>>(
    defaultParams("moving_average_cross"),
  );

  useEffect(() => {
    if (open) {
      if (initialPreset) {
        setName(initialPreset.name);
        const t = initialPreset.type as StrategyTypeValue;
        setType(t);
        setParams({ ...defaultParams(t), ...initialPreset.params });
      } else {
        setName("");
        setType("moving_average_cross");
        setParams(defaultParams("moving_average_cross"));
      }
    }
  }, [open, initialPreset]);

  function handleTypeChange(newType: StrategyTypeValue) {
    setType(newType);
    setParams(defaultParams(newType));
  }

  function handleSubmit() {
    if (!name.trim()) return;
    onSave({ name: name.trim(), type, params }, isNew);
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm" />
        <Dialog.Content
          data-testid="preset-dialog"
          className="fixed left-1/2 top-1/2 z-50 w-[480px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
        >
          <div className="mb-4 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold text-slate-100">
              {isNew ? "新增策略 Preset" : "編輯策略 Preset"}
            </Dialog.Title>
            <Dialog.Close
              data-testid="preset-dialog-close"
              className="-mr-1 -mt-1 rounded-md p-1 text-slate-500 hover:text-slate-300"
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="space-y-4">
            <div>
              <label className="mb-1 block text-xs text-slate-400">名稱</label>
              <input
                data-testid="preset-name-input"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="策略名稱"
                className="w-full rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100 placeholder:text-slate-500"
              />
            </div>

            <div>
              <label className="mb-1 block text-xs text-slate-400">策略類型</label>
              <select
                data-testid="preset-type-select"
                value={type}
                onChange={(e) =>
                  handleTypeChange(e.target.value as StrategyTypeValue)
                }
                className="w-full rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
              >
                {STRATEGY_TYPES.map((st) => (
                  <option key={st.value} value={st.value}>
                    {st.value} ({st.label})
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <span className="text-xs text-slate-400">參數</span>
              {PARAM_SPECS[type].map((spec) => (
                <div key={spec.key} className="flex items-center gap-3">
                  <label className="w-40 shrink-0 text-xs text-slate-400">
                    {spec.label}
                  </label>
                  <input
                    data-testid={`param-${spec.key}`}
                    type="number"
                    value={params[spec.key] ?? spec.defaultValue}
                    onChange={(e) =>
                      setParams((prev) => ({
                        ...prev,
                        [spec.key]: Number(e.target.value),
                      }))
                    }
                    className="flex-1 rounded border border-slate-700 bg-slate-800 px-3 py-1.5 text-sm text-slate-100"
                  />
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6 flex justify-end gap-2 border-t border-slate-800 pt-4">
            <button
              data-testid="preset-dialog-cancel"
              onClick={onClose}
              className="rounded border border-slate-700 px-4 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
            >
              取消
            </button>
            <button
              data-testid="preset-dialog-submit"
              onClick={handleSubmit}
              disabled={!name.trim()}
              className="rounded bg-blue-600 px-4 py-1.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-50"
            >
              {isNew ? "新增" : "儲存"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
