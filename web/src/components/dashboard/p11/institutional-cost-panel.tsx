import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11InstitutionalCostResponse } from "@/types/analysis";

function renderPrice(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return formatNumber(value, 2);
}

function pnlClass(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "text-slate-300";
  if (value > 0) return "text-rise";
  if (value < 0) return "text-fall";
  return "text-slate-300";
}

function pnlText(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  const sign = value > 0 ? "+" : "";
  return `${sign}${formatNumber(value, 2)}`;
}

export function InstitutionalCostPanel({ data }: { data: P11InstitutionalCostResponse | undefined }) {
  const rows = [
    { key: "foreign", label: "外資", value: data?.foreign },
    { key: "trust", label: "投信", value: data?.trust },
    { key: "dealer", label: "自營商", value: data?.dealer },
  ] as const;

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-institutional-cost">
      <div className="mb-2 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-slate-100">法人持股成本</h3>
        <HelpTooltip text={P11_TOOLTIP_TEXT.institutional_cost} />
      </div>
      <div className="overflow-hidden rounded-md border border-slate-800">
        <table className="w-full text-xs">
          <thead className="bg-slate-900/80 text-slate-300">
            <tr>
              <th className="px-2 py-1.5 text-left">法人</th>
              <th className="px-2 py-1.5 text-right">成本</th>
              <th className="px-2 py-1.5 text-right">浮盈虧</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.key} className="border-t border-slate-800">
                <td className="px-2 py-1.5 text-slate-100">{row.label}</td>
                <td className="px-2 py-1.5 text-right text-slate-100 [font-family:var(--font-mono)]">
                  {renderPrice(row.value?.cost ?? null)}
                </td>
                <td
                  className={`px-2 py-1.5 text-right [font-family:var(--font-mono)] ${pnlClass(row.value?.pnl ?? null)}`}
                  data-testid={`p11-institutional-pnl-${row.key}`}
                >
                  {pnlText(row.value?.pnl ?? null)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
