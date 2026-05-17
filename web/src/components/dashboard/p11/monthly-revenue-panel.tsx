import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11MonthlyRevenueResponse } from "@/types/analysis";

function formatRevenueYi(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${formatNumber(value / 100_000_000, 1)} 億`;
}

function pctClass(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "text-slate-300";
  if (value > 0) return "text-rise";
  if (value < 0) return "text-fall";
  return "text-slate-300";
}

export function MonthlyRevenuePanel({ data }: { data: P11MonthlyRevenueResponse | undefined }) {
  const items = data?.items ?? [];
  const values = items.map((item) => item.revenue ?? 0);
  const max = values.length > 0 ? Math.max(...values, 1) : 1;
  const latest = items[items.length - 1];

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-monthly-revenue">
      <div className="mb-2 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-slate-100">月營收</h3>
        <HelpTooltip text={P11_TOOLTIP_TEXT.monthly_revenue} />
      </div>
      <div className="mb-2 grid grid-cols-2 gap-2 text-xs">
        <div>
          <div className="text-slate-400">最新月份</div>
          <div className="text-slate-100 [font-family:var(--font-mono)]">{data?.latest_month ?? "—"}</div>
        </div>
        <div>
          <div className="text-slate-400">營收</div>
          <div className="text-slate-100 [font-family:var(--font-mono)]">{formatRevenueYi(data?.latest_revenue ?? null)}</div>
        </div>
        <div>
          <div className="text-slate-400">年增率</div>
          <div className={`${pctClass(latest?.yoy ?? null)} [font-family:var(--font-mono)]`}>
            {latest?.yoy == null ? "—" : `${formatNumber(latest.yoy, 1)}%`}
          </div>
        </div>
        <div>
          <div className="text-slate-400">月增率</div>
          <div className={`${pctClass(latest?.mom ?? null)} [font-family:var(--font-mono)]`}>
            {latest?.mom == null ? "—" : `${formatNumber(latest.mom, 1)}%`}
          </div>
        </div>
      </div>
      <div className="rounded-md border border-slate-800 bg-slate-900/40 p-2">
        <div className="mb-1 text-xs text-slate-400">近 12 月趨勢</div>
        <div className="flex h-14 items-end gap-1" data-testid="p11-monthly-revenue-sparkline">
          {(items.length > 0 ? items : Array.from({ length: 12 }, () => null)).map((item, idx, arr) => {
            const value = item?.revenue ?? 0;
            const height = Math.max(8, Math.round((value / max) * 52));
            const isLast = idx === arr.length - 1;
            return (
              <div
                key={`${idx}-${item?.date ?? "empty"}`}
                className={isLast ? "flex-1 rounded-t bg-primary" : "flex-1 rounded-t bg-slate-600"}
                style={{ height: `${height}px` }}
              />
            );
          })}
        </div>
      </div>
    </section>
  );
}
