import { Pencil } from "lucide-react";
import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11DividendPolicyFallback, P11EventCalendarEntry, P11EventCalendarResponse } from "@/types/analysis";

function renderCountdown(daysUntil: number | null | undefined): string {
  if (daysUntil == null || Number.isNaN(daysUntil)) return "—";
  return `倒數 ${formatNumber(daysUntil, 0)} 天`;
}

function MeetingLine({ entry, showCountdown }: { entry: P11EventCalendarEntry | null; showCountdown: boolean }) {
  if (!entry) return <span className="text-slate-500">—</span>;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-slate-100 [font-family:var(--font-mono)]">{entry.date}</span>
      {entry.meeting_type ? <span className="text-slate-300">{entry.meeting_type}</span> : null}
      {entry.is_manual ? (
        <span className="rounded border border-amber-600/60 bg-amber-500/15 px-1.5 py-0.5 text-[10px] text-amber-200">[手動設定]</span>
      ) : null}
      {showCountdown ? <span className="text-slate-400">{renderCountdown(entry.days_until)}</span> : null}
    </div>
  );
}

function DividendLine({ entry, showCountdown }: { entry: P11EventCalendarEntry | null; showCountdown: boolean }) {
  if (!entry) return <span className="text-slate-500">—</span>;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <span className="text-slate-100 [font-family:var(--font-mono)]">{entry.date}</span>
      <span className="text-slate-300">現金股利 {entry.cash_dividend == null ? "—" : formatNumber(entry.cash_dividend, 2)}</span>
      {entry.stock_dividend != null && entry.stock_dividend > 0 ? (
        <span className="text-slate-300">股票股利 {formatNumber(entry.stock_dividend, 2)}</span>
      ) : null}
      {showCountdown ? <span className="text-slate-400">{renderCountdown(entry.days_until)}</span> : null}
    </div>
  );
}

function DividendPolicyFallbackLine({ fallback }: { fallback: P11DividendPolicyFallback | null | undefined }) {
  if (!fallback) return <span className="text-slate-500">—</span>;

  if (fallback.status === "current_year") {
    return (
      <div className="flex flex-wrap items-start gap-1" data-testid="p11-dividend-fallback-current">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-slate-300">今年股利資料</span>
          {fallback.period ? (
            <span className="text-slate-100 [font-family:var(--font-mono)]">{fallback.period}</span>
          ) : null}
          {fallback.payment_status === "undetermined" ? (
            <span className="text-slate-400">股利發放時間未定</span>
          ) : null}
          {fallback.cash_dividend != null ? (
            <span className="text-slate-300">現金股利 {formatNumber(fallback.cash_dividend, 2)}</span>
          ) : null}
          {fallback.stock_dividend != null && fallback.stock_dividend > 0 ? (
            <span className="text-slate-300">股票股利 {formatNumber(fallback.stock_dividend, 2)}</span>
          ) : null}
        </div>
        <div className="w-full text-slate-500">
          <a
            href={fallback.source_url}
            target="_blank"
            rel="noopener noreferrer"
            className="underline hover:text-slate-300"
            data-testid="p11-dividend-fallback-link"
          >
            Goodinfo 來源
          </a>
          <span className="ml-1">{fallback.source_note}</span>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="p11-dividend-fallback-not-found">
      <span className="text-slate-500">查無今年股利資料</span>
      <a
        href={fallback.source_url}
        target="_blank"
        rel="noopener noreferrer"
        className="text-slate-500 underline hover:text-slate-300"
        data-testid="p11-dividend-fallback-link"
      >
        Goodinfo 來源
      </a>
    </div>
  );
}

export function EventCalendarPanel({
  data,
  onEdit,
}: {
  data: P11EventCalendarResponse | undefined;
  onEdit: () => void;
}) {
  const missing = data?.missing_shareholder_meeting ?? true;
  const isEtf = data?.is_etf ?? false;
  const missingText = isEtf
    ? "撈不到資料，需要手動填入（ETF沒有股東會）"
    : "撈不到資料，需要手動填入";

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-event-calendar">
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="flex items-center gap-1">
          <h3 className="text-sm font-semibold text-slate-100">事件行事曆</h3>
          <HelpTooltip text={P11_TOOLTIP_TEXT.event_calendar} />
        </div>
        <button
          type="button"
          className="rounded-md border border-slate-700 p-1 text-slate-300 hover:bg-slate-800"
          aria-label="edit-shareholder-meeting"
          onClick={onEdit}
        >
          <Pencil className="h-3.5 w-3.5" />
        </button>
      </div>

      {missing ? (
        <p className="mb-2 text-xs text-amber-300" data-testid="p11-shareholder-missing">
          {missingText}
        </p>
      ) : null}

      <div className="space-y-2 text-xs">
        <div className="rounded border border-slate-800 bg-slate-900/40 p-2">
          <div className="mb-1 text-slate-400">即將</div>
          <div className="space-y-1">
            <div>
              <span className="mr-2 text-slate-500">除息</span>
              {data?.next_ex_dividend != null ? (
                <DividendLine entry={data.next_ex_dividend} showCountdown />
              ) : (
                <DividendPolicyFallbackLine fallback={data?.dividend_policy_fallback} />
              )}
            </div>
            <div>
              <span className="mr-2 text-slate-500">股東會</span>
              <MeetingLine entry={data?.next_shareholder_meeting ?? null} showCountdown />
            </div>
          </div>
        </div>
        <div className="rounded border border-slate-800 bg-slate-900/40 p-2">
          <div className="mb-1 text-slate-400">上次</div>
          <div className="space-y-1">
            <div>
              <span className="mr-2 text-slate-500">除息</span>
              <DividendLine entry={data?.last_ex_dividend ?? null} showCountdown={false} />
            </div>
            <div data-testid="p11-last-shareholder-row">
              <span className="mr-2 text-slate-500">股東會</span>
              <MeetingLine entry={data?.last_shareholder_meeting ?? null} showCountdown={false} />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
