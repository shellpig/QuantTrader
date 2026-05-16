"use client";

// WFA Window table — one row per rolling window (Phase 10-E-4)

export interface WfaWindowRow {
  window_id: number;
  is_start: string;
  is_end: string;
  oos_start: string;
  oos_end: string;
  best_params: Record<string, number> | null;
  is_metrics: { sharpe_ratio?: number; total_return?: number } | null;
  oos_metrics: { sharpe_ratio?: number; total_return?: number; max_drawdown?: number } | null;
  degradation: number | null;
  skipped: boolean;
  warnings: string[];
}

interface WfaWindowTableProps {
  windows: WfaWindowRow[];
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function fmtNum(v: number | null | undefined, d = 2): string {
  if (v == null) return "—";
  return v.toFixed(d);
}

function ParamChips({ params }: { params: Record<string, number> | null }) {
  if (!params) return <span className="text-slate-500">—</span>;
  return (
    <div className="flex flex-wrap gap-1">
      {Object.entries(params).map(([k, v]) => (
        <span
          key={k}
          className="rounded bg-slate-700 px-1.5 py-0.5 text-xs text-slate-200"
        >
          {k}={v}
        </span>
      ))}
    </div>
  );
}

export function WfaWindowTable({ windows }: WfaWindowTableProps) {
  if (windows.length === 0) {
    return <p className="text-sm text-slate-500">尚無視窗結果</p>;
  }

  return (
    <div data-testid="wfa-window-table" className="overflow-x-auto">
      <table className="w-full min-w-[800px] text-sm">
        <thead>
          <tr className="border-b border-slate-700 text-xs text-slate-400">
            <th className="px-2 py-2 text-left">#</th>
            <th className="px-2 py-2 text-left">IS 期</th>
            <th className="px-2 py-2 text-left">OOS 期</th>
            <th className="px-2 py-2 text-left">最佳參數</th>
            <th className="px-2 py-2 text-right">IS Sharpe</th>
            <th className="px-2 py-2 text-right">OOS Sharpe</th>
            <th className="px-2 py-2 text-right">Degradation</th>
            <th className="px-2 py-2 text-left">警告</th>
          </tr>
        </thead>
        <tbody>
          {windows.map((w) => {
            const degradation = w.degradation;
            const isDegraded = degradation != null && degradation < -0.3;
            return (
              <tr
                key={w.window_id}
                data-testid={`wfa-window-row-${w.window_id}`}
                className={`border-b border-slate-800 ${w.skipped ? "opacity-50" : ""}`}
              >
                <td className="px-2 py-2 text-slate-300">{w.window_id}</td>
                <td className="px-2 py-2 text-slate-300 tabular-nums">
                  {w.is_start} ~ {w.is_end}
                </td>
                <td className="px-2 py-2 text-slate-300 tabular-nums">
                  {w.oos_start} ~ {w.oos_end}
                </td>
                <td className="px-2 py-2">
                  {w.skipped ? (
                    <span className="text-xs text-slate-500">已跳過</span>
                  ) : (
                    <ParamChips params={w.best_params} />
                  )}
                </td>
                <td className="px-2 py-2 text-right tabular-nums text-slate-300">
                  {fmtNum(w.is_metrics?.sharpe_ratio)}
                </td>
                <td className="px-2 py-2 text-right tabular-nums text-slate-300">
                  {fmtNum(w.oos_metrics?.sharpe_ratio)}
                </td>
                <td
                  data-testid={`degradation-${w.window_id}`}
                  className={`px-2 py-2 text-right tabular-nums ${isDegraded ? "font-semibold text-red-400" : "text-slate-300"}`}
                >
                  {fmtNum(degradation, 4)}
                </td>
                <td className="px-2 py-2">
                  {w.warnings.length > 0 ? (
                    <span
                      className="text-xs text-amber-400"
                      title={w.warnings.join("\n")}
                    >
                      ⚠ {w.warnings[0]}
                    </span>
                  ) : null}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
