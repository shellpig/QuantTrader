"use client";

import { useMemo, useState } from "react";
import type { SweepResultRow } from "./sweep-types";

type SortKey =
  | "sharpe_ratio"
  | "total_return"
  | "annual_return"
  | "max_drawdown"
  | "win_rate"
  | "total_trades";

interface SweepRankingTableProps {
  rows: SweepResultRow[];
  topN?: number;
}

function fmtPct(value: number | null): string {
  if (value == null) return "—";
  return `${(value * 100).toFixed(2)}%`;
}

function fmtNum(value: number | null): string {
  if (value == null) return "—";
  return value.toFixed(2);
}

function paramLabel(params: Record<string, number>): string {
  const entries = Object.entries(params).sort(([a], [b]) => a.localeCompare(b));
  return entries.map(([k, v]) => `${k}=${v}`).join(", ");
}

export function SweepRankingTable({ rows, topN = 20 }: SweepRankingTableProps) {
  const [sortKey, setSortKey] = useState<SortKey>("sharpe_ratio");
  const [sortAsc, setSortAsc] = useState(false);

  const sorted = useMemo(() => {
    const next = [...rows];
    next.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const an = typeof av === "number" ? av : Number.NEGATIVE_INFINITY;
      const bn = typeof bv === "number" ? bv : Number.NEGATIVE_INFINITY;
      const cmp = an - bn;
      return sortAsc ? cmp : -cmp;
    });
    return next.slice(0, topN);
  }, [rows, sortKey, sortAsc, topN]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortAsc((v) => !v);
      return;
    }
    setSortKey(key);
    setSortAsc(false);
  }

  function mark(key: SortKey) {
    if (sortKey !== key) return "↕";
    return sortAsc ? "↑" : "↓";
  }

  if (rows.length === 0) {
    return (
      <div
        data-testid="sweep-ranking-empty"
        className="rounded-lg border border-slate-700 p-4 text-sm text-slate-400"
      >
        尚無掃描結果。
      </div>
    );
  }

  const th = "cursor-pointer select-none px-2 py-2 text-left text-xs text-slate-400 hover:text-slate-200";
  const td = "px-2 py-2 text-sm text-slate-100 align-top";

  return (
    <div data-testid="sweep-ranking-table" className="overflow-x-auto rounded-lg border border-slate-700">
      <table className="min-w-full">
        <thead className="border-b border-slate-700 bg-slate-800/40">
          <tr>
            <th className="px-2 py-2 text-left text-xs text-slate-400">排名</th>
            <th className="px-2 py-2 text-left text-xs text-slate-400">參數組合</th>
            <th className={th} onClick={() => toggleSort("sharpe_ratio")}>Sharpe {mark("sharpe_ratio")}</th>
            <th className={th} onClick={() => toggleSort("total_return")}>總報酬 {mark("total_return")}</th>
            <th className={th} onClick={() => toggleSort("annual_return")}>年化 {mark("annual_return")}</th>
            <th className={th} onClick={() => toggleSort("max_drawdown")}>最大回撤 {mark("max_drawdown")}</th>
            <th className={th} onClick={() => toggleSort("win_rate")}>勝率 {mark("win_rate")}</th>
            <th className={th} onClick={() => toggleSort("total_trades")}>交易次數 {mark("total_trades")}</th>
            <th className="px-2 py-2 text-left text-xs text-slate-400">警告</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((row, idx) => (
            <tr key={`${paramLabel(row.params)}-${idx}`} className="border-b border-slate-800">
              <td className={td}>{idx + 1}</td>
              <td className={td}>
                <div className="flex flex-wrap gap-1">
                  {Object.entries(row.params).map(([k, v]) => (
                    <span
                      key={k}
                      className="rounded bg-slate-800 px-1.5 py-0.5 text-xs text-slate-300"
                    >
                      {k}={v}
                    </span>
                  ))}
                </div>
                {row.error && (
                  <div className="mt-1 text-xs text-rose-300">{row.error}</div>
                )}
              </td>
              <td className={td}>{fmtNum(row.sharpe_ratio)}</td>
              <td className={td}>{fmtPct(row.total_return)}</td>
              <td className={td}>{fmtPct(row.annual_return)}</td>
              <td className={td}>{fmtPct(row.max_drawdown)}</td>
              <td className={td}>{fmtPct(row.win_rate)}</td>
              <td className={td}>{row.total_trades}</td>
              <td className={td}>
                {row.sample_warning ? (
                  <span
                    data-testid="sample-warning-icon"
                    className="inline-flex cursor-help rounded bg-amber-500/20 px-1.5 py-0.5 text-xs text-amber-300"
                    title="樣本數 < 3"
                  >
                    !
                  </span>
                ) : (
                  "—"
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
