"use client";

// WFA Summary cards — 5 OOS metrics + avg degradation chip (Phase 10-E-4)

interface WfaAggregate {
  oos_total_return: number | null;
  oos_annual_return: number | null;
  oos_max_drawdown: number | null;
  oos_sharpe_ratio: number | null;
  oos_win_rate: number | null;
  avg_degradation: number | null;
}

interface WfaSummaryCardsProps {
  aggregate: WfaAggregate;
  validWindowCount: number;
  totalWindowCount: number;
  currency?: string;
}

function fmtPct(v: number | null | undefined): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(2)}%`;
}

function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v == null) return "—";
  return v.toFixed(decimals);
}

function MetricCard({
  label,
  value,
  colorClass,
}: {
  label: string;
  value: string;
  colorClass?: string;
}) {
  return (
    <div
      data-testid="wfa-metric-card"
      className="rounded-lg border border-slate-700 bg-slate-800 p-3"
    >
      <p className="text-xs text-slate-400">{label}</p>
      <p className={`mt-1 text-lg font-semibold tabular-nums ${colorClass ?? "text-slate-100"}`}>
        {value}
      </p>
    </div>
  );
}

export function WfaSummaryCards({
  aggregate,
  validWindowCount,
  totalWindowCount,
  currency = "TWD",
}: WfaSummaryCardsProps) {
  const totalReturn = aggregate.oos_total_return;
  const drawdown = aggregate.oos_max_drawdown;
  const sharpe = aggregate.oos_sharpe_ratio;
  const winRate = aggregate.oos_win_rate;
  const degradation = aggregate.avg_degradation;

  const returnColor =
    totalReturn == null ? "" : totalReturn >= 0 ? "text-green-400" : "text-red-400";
  const drawdownColor = "text-red-400";
  const sharpeColor = sharpe == null ? "" : sharpe >= 0.5 ? "text-green-400" : "text-amber-400";
  const degradationColor =
    degradation == null ? "" : degradation >= 0 ? "text-green-400" : "text-red-400";

  return (
    <div data-testid="wfa-summary-cards" className="space-y-3">
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-5">
        <MetricCard
          label="OOS 平均報酬"
          value={fmtPct(totalReturn)}
          colorClass={returnColor}
        />
        <MetricCard
          label="OOS 最大回撤"
          value={fmtPct(drawdown)}
          colorClass={drawdownColor}
        />
        <MetricCard
          label="OOS 平均 Sharpe"
          value={fmtNum(sharpe)}
          colorClass={sharpeColor}
        />
        <MetricCard label="OOS 勝率 (視窗)" value={fmtPct(winRate)} />
        <MetricCard
          label={`有效視窗 (${currency})`}
          value={`${validWindowCount} / ${totalWindowCount}`}
        />
      </div>

      {degradation != null && (
        <div
          data-testid="wfa-degradation-chip"
          className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1 text-sm ${
            degradation >= 0
              ? "border-green-500/30 bg-green-500/10 text-green-400"
              : "border-red-500/30 bg-red-500/10 text-red-400"
          }`}
        >
          <span>IS → OOS 平均退化</span>
          <span className="font-semibold tabular-nums">{fmtNum(degradation, 4)}</span>
        </div>
      )}
    </div>
  );
}
