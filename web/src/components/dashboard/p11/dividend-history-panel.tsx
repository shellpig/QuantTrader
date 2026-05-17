import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11DividendHistoryResponse } from "@/types/analysis";

function renderValue(value: number | null, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return formatNumber(value, digits);
}

export function DividendHistoryPanel({ data }: { data: P11DividendHistoryResponse | undefined }) {
  const items = data?.items ?? [];
  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-historical-dividend-pe">
      <div className="mb-2 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-slate-100">歷史除息本益比</h3>
        <HelpTooltip text={P11_TOOLTIP_TEXT.historical_dividend_pe} />
      </div>
      <div className="overflow-hidden rounded-md border border-slate-800">
        <table className="w-full text-xs">
          <thead className="bg-slate-900/80 text-slate-300">
            <tr>
              <th className="px-2 py-1.5 text-left">除息日</th>
              <th className="px-2 py-1.5 text-right">現金股息</th>
              <th className="px-2 py-1.5 text-right">
                <span className="inline-flex items-center gap-1">
                  TTM 本益比
                  <HelpTooltip text={P11_TOOLTIP_TEXT.ttm_pe} />
                </span>
              </th>
            </tr>
          </thead>
          <tbody>
            {(items.length > 0 ? items : Array.from({ length: 5 }, () => null)).map((row, idx) => (
              <tr key={`${row?.date ?? "empty"}-${idx}`} className="border-t border-slate-800">
                <td className="px-2 py-1.5 text-slate-100 [font-family:var(--font-mono)]">{row?.date ?? "—"}</td>
                <td className="px-2 py-1.5 text-right text-slate-100 [font-family:var(--font-mono)]">
                  {row ? renderValue(row.cash_dividend, 2) : "—"}
                </td>
                <td className="px-2 py-1.5 text-right text-slate-100 [font-family:var(--font-mono)]">
                  {row ? renderValue(row.ttm_pe, 2) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
