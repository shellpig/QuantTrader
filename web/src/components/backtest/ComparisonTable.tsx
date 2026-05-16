"use client";

import { useMemo, useState } from "react";
import type { ReactNode } from "react";
import type { BacktestBatchSummary } from "./batch-types";

type SortKey =
  | "preset_name"
  | "strategy_type"
  | "total_return"
  | "annual_return"
  | "max_drawdown"
  | "sharpe_ratio"
  | "win_rate"
  | "profit_factor"
  | "total_trades";

interface ComparisonTableProps {
  summaries: BacktestBatchSummary[];
  expandedPresetIndex: number | null;
  onToggleExpand: (presetIndex: number) => void;
  renderExpanded?: (summary: BacktestBatchSummary) => ReactNode;
}

function fmtPct(value: number | null): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

function fmtNum(value: number | null, digits = 2): string {
  if (value == null) return "—";
  return value.toFixed(digits);
}

export function ComparisonTable({
  summaries,
  expandedPresetIndex,
  onToggleExpand,
  renderExpanded,
}: ComparisonTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("sharpe_ratio");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    const rows = [...summaries];
    rows.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];

      if (typeof av === "string" && typeof bv === "string") {
        const cmp = av.localeCompare(bv);
        return sortAsc ? cmp : -cmp;
      }

      const an = typeof av === "number" ? av : Number.NEGATIVE_INFINITY;
      const bn = typeof bv === "number" ? bv : Number.NEGATIVE_INFINITY;
      const cmp = an - bn;
      return sortAsc ? cmp : -cmp;
    });
    return rows;
  }, [sortAsc, sortKey, summaries]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((v) => !v);
      return;
    }
    setSortKey(key);
    setSortAsc(false);
  }

  function sortMark(key: SortKey): string {
    if (sortKey !== key) return "↕";
    return sortAsc ? "↑" : "↓";
  }

  const th = "cursor-pointer select-none px-2 py-2 text-left text-xs text-slate-400 hover:text-slate-200";
  const td = "px-2 py-2 text-sm text-slate-100";

  return (
    <div data-testid="comparison-table" className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="min-w-full">
        <thead className="border-b border-slate-700 bg-slate-800/40">
          <tr>
            <th className={th} onClick={() => toggleSort("preset_name")}>策略 {sortMark("preset_name")}</th>
            <th className={th} onClick={() => toggleSort("strategy_type")}>類型 {sortMark("strategy_type")}</th>
            <th className={th} onClick={() => toggleSort("total_return")}>總報酬 {sortMark("total_return")}</th>
            <th className={th} onClick={() => toggleSort("annual_return")}>年化 {sortMark("annual_return")}</th>
            <th className={th} onClick={() => toggleSort("max_drawdown")}>最大回撤 {sortMark("max_drawdown")}</th>
            <th className={th} onClick={() => toggleSort("sharpe_ratio")}>Sharpe {sortMark("sharpe_ratio")}</th>
            <th className={th} onClick={() => toggleSort("win_rate")}>勝率 {sortMark("win_rate")}</th>
            <th className={th} onClick={() => toggleSort("profit_factor")}>PF {sortMark("profit_factor")}</th>
            <th className={th} onClick={() => toggleSort("total_trades")}>交易數 {sortMark("total_trades")}</th>
            <th className="px-2 py-2 text-left text-xs text-slate-400">錯誤 / 展開</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((s) => {
            const isExpanded = expandedPresetIndex === s.preset_index;
            return (
              <tr key={s.preset_index} className="border-b border-slate-800 align-top">
                <td className={td}>{s.preset_name}</td>
                <td className={td}>{s.strategy_type}</td>
                <td className={td}>{fmtPct(s.total_return)}</td>
                <td className={td}>{fmtPct(s.annual_return)}</td>
                <td className={td}>{fmtPct(s.max_drawdown)}</td>
                <td className={td}>{fmtNum(s.sharpe_ratio, 2)}</td>
                <td className={td}>{fmtPct(s.win_rate)}</td>
                <td className={td}>{fmtNum(s.profit_factor, 2)}</td>
                <td className={td}>{s.total_trades}</td>
                <td className={td}>
                  {s.error ? (
                    <span className="text-xs text-amber-300">{s.error}</span>
                  ) : (
                    <button
                      type="button"
                      data-testid={`expand-row-${s.preset_index}`}
                      className="rounded bg-slate-700 px-2 py-1 text-xs text-slate-100 hover:bg-slate-600"
                      onClick={() => onToggleExpand(s.preset_index)}
                    >
                      {isExpanded ? "收合" : "展開"}
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {expandedPresetIndex != null && renderExpanded && (
        <div data-testid="comparison-table-expanded" className="border-t border-slate-700 bg-slate-900/40 p-3">
          {(() => {
            const target = summaries.find((s) => s.preset_index === expandedPresetIndex);
            return target ? renderExpanded(target) : null;
          })()}
        </div>
      )}
    </div>
  );
}

