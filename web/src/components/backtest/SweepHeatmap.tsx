"use client";

import { useMemo, useState } from "react";
import type { SweepResultRow } from "./sweep-types";

interface SweepHeatmapProps {
  rows: SweepResultRow[];
  onCopyParams?: (params: Record<string, number>) => void;
}

function clamp01(value: number): number {
  if (value < 0) return 0;
  if (value > 1) return 1;
  return value;
}

function heatColor(value: number, min: number, max: number): string {
  if (max <= min) return "rgba(250,204,21,0.55)";
  const t = clamp01((value - min) / (max - min));
  if (t < 0.5) {
    const u = t / 0.5;
    const r = 239;
    const g = Math.round(68 + (204 - 68) * u);
    const b = 68;
    return `rgba(${r},${g},${b},0.65)`;
  }
  const u = (t - 0.5) / 0.5;
  const r = Math.round(250 + (34 - 250) * u);
  const g = Math.round(204 + (197 - 204) * u);
  const b = Math.round(21 + (94 - 21) * u);
  return `rgba(${r},${g},${b},0.65)`;
}

interface TooltipState {
  x: number;
  y: number;
  row: SweepResultRow;
}

export function SweepHeatmap({ rows, onCopyParams }: SweepHeatmapProps) {
  const [tooltip, setTooltip] = useState<TooltipState | null>(null);

  const validRows = useMemo(
    () => rows.filter((r) => r.error == null && r.sharpe_ratio != null),
    [rows],
  );
  const paramKeys = useMemo(() => {
    if (validRows.length === 0) return [];
    return Object.keys(validRows[0].params).sort();
  }, [validRows]);

  if (paramKeys.length !== 2) {
    return null;
  }

  const [xKey, yKey] = paramKeys;
  const xValues = Array.from(new Set(validRows.map((r) => Number(r.params[xKey])))).sort((a, b) => a - b);
  const yValues = Array.from(new Set(validRows.map((r) => Number(r.params[yKey])))).sort((a, b) => a - b);
  const sharpeValues = validRows.map((r) => Number(r.sharpe_ratio));
  const minSharpe = Math.min(...sharpeValues);
  const maxSharpe = Math.max(...sharpeValues);

  const byPair = new Map<string, SweepResultRow>();
  for (const row of validRows) {
    byPair.set(`${row.params[xKey]}__${row.params[yKey]}`, row);
  }

  return (
    <div data-testid="sweep-heatmap" className="space-y-2 rounded-lg border border-slate-700 p-3">
      <div className="text-sm text-slate-300">2D Heatmap（Sharpe）</div>
      <div className="text-xs text-slate-400">X: {xKey} / Y: {yKey}</div>

      <div className="overflow-x-auto">
        <div
          className="grid gap-1"
          style={{ gridTemplateColumns: `80px repeat(${xValues.length}, minmax(48px, 1fr))` }}
        >
          <div />
          {xValues.map((xVal) => (
            <div key={`x-${xVal}`} className="text-center text-xs text-slate-400">
              {xVal}
            </div>
          ))}

          {yValues.map((yVal) => (
            <div key={`row-${yVal}`} className="contents">
              <div className="text-right text-xs text-slate-400">{yVal}</div>
              {xValues.map((xVal) => {
                const row = byPair.get(`${xVal}__${yVal}`);
                const sharpe = row?.sharpe_ratio;
                const bg =
                  sharpe == null
                    ? "rgba(51,65,85,0.35)"
                    : heatColor(Number(sharpe), minSharpe, maxSharpe);
                return (
                  <button
                    key={`cell-${xVal}-${yVal}`}
                    type="button"
                    data-testid="sweep-heatmap-cell"
                    className="h-10 rounded text-xs text-slate-900"
                    style={{ backgroundColor: bg }}
                    onMouseEnter={(e) => {
                      if (!row) return;
                      const rect = (e.currentTarget.parentElement as HTMLElement | null)?.getBoundingClientRect();
                      const self = e.currentTarget.getBoundingClientRect();
                      setTooltip({
                        x: rect ? self.left - rect.left : 0,
                        y: rect ? self.top - rect.top : 0,
                        row,
                      });
                    }}
                    onMouseLeave={() => setTooltip(null)}
                    onClick={() => {
                      if (!row) return;
                      onCopyParams?.(row.params);
                    }}
                    title={row ? `${xKey}=${xVal}, ${yKey}=${yVal}, Sharpe=${Number(sharpe).toFixed(2)}` : "無資料"}
                  >
                    {sharpe == null ? "—" : Number(sharpe).toFixed(2)}
                  </button>
                );
              })}
            </div>
          ))}
        </div>
      </div>

      {tooltip && (
        <div
          data-testid="sweep-heatmap-tooltip"
          className="rounded border border-slate-700 bg-slate-900/95 px-2 py-1 text-xs text-slate-200"
          style={{ transform: `translate(${tooltip.x}px, ${tooltip.y}px)` }}
        >
          <div className="font-medium text-slate-300">
            {xKey}={tooltip.row.params[xKey]}, {yKey}={tooltip.row.params[yKey]}
          </div>
          <div>Sharpe: {tooltip.row.sharpe_ratio?.toFixed(2) ?? "—"}</div>
          <div>總報酬: {tooltip.row.total_return != null ? `${(tooltip.row.total_return * 100).toFixed(2)}%` : "—"}</div>
          <div>年化: {tooltip.row.annual_return != null ? `${(tooltip.row.annual_return * 100).toFixed(2)}%` : "—"}</div>
          <div>最大回撤: {tooltip.row.max_drawdown != null ? `${(tooltip.row.max_drawdown * 100).toFixed(2)}%` : "—"}</div>
          <div>勝率: {tooltip.row.win_rate != null ? `${(tooltip.row.win_rate * 100).toFixed(2)}%` : "—"}</div>
          <div>交易次數: {tooltip.row.total_trades}</div>
        </div>
      )}
    </div>
  );
}
