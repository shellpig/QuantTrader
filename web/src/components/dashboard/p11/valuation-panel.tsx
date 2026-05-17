import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11ValuationResponse } from "@/types/analysis";

function renderNumber(value: number | null, digits = 2): string {
  if (value === null || Number.isNaN(value)) return "—";
  return formatNumber(value, digits);
}

export function ValuationPanel({
  data,
  onOpenIndustry,
}: {
  data: P11ValuationResponse | undefined;
  onOpenIndustry: () => void;
}) {
  const noData =
    data !== undefined &&
    data.per === null &&
    data.pbr === null &&
    data.dividend_yield === null;

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-pe-ratio">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <h3 className="text-sm font-semibold text-slate-100">本益比</h3>
          <HelpTooltip text={P11_TOOLTIP_TEXT.pe_ratio} />
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-700 px-2 py-1 text-xs text-slate-300 hover:bg-slate-800"
          onClick={onOpenIndustry}
        >
          同產業 -&gt;
        </button>
      </div>
      {noData ? (
        <p className="text-xs text-slate-500" data-testid="p11-valuation-unsupported">
          資料源未提供此標的估值資料（如 ETF）
        </p>
      ) : (
        <div className="space-y-1.5 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-slate-400">本益比</span>
            <span className="text-slate-100 [font-family:var(--font-mono)]">{renderNumber(data?.per ?? null)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">股價淨值比</span>
            <span className="text-slate-100 [font-family:var(--font-mono)]">{renderNumber(data?.pbr ?? null)}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-slate-400">殖利率</span>
            <span className="text-slate-100 [font-family:var(--font-mono)]">
              {data?.dividend_yield == null ? "—" : `${renderNumber(data.dividend_yield, 2)}%`}
            </span>
          </div>
        </div>
      )}
    </section>
  );
}
