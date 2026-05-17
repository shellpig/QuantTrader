"use client";

import { useState } from "react";
import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11MonthlyRevenueItem, P11MonthlyRevenueResponse } from "@/types/analysis";

const SPARKLINE_BARS = 12;

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

function pctText(value: number | null): string {
  if (value == null || Number.isNaN(value)) return "—";
  return `${value > 0 ? "+" : ""}${formatNumber(value, 1)}%`;
}

function BarTooltip({ item, side }: { item: P11MonthlyRevenueItem; side: "left" | "right" }) {
  const monthLabel = `${item.revenue_year}-${String(item.revenue_month).padStart(2, "0")}`;
  const posClass = side === "right" ? "right-0" : "left-0";
  return (
    <div
      className={`absolute top-0 z-10 min-w-[120px] rounded border border-slate-700 bg-slate-800 px-2.5 py-1.5 text-xs text-slate-200 shadow-lg ${posClass}`}
      data-testid="revenue-bar-tooltip"
    >
      <div className="mb-0.5 font-medium text-slate-100">{monthLabel}</div>
      <div>營收：{formatRevenueYi(item.revenue)}</div>
      <div>
        年增率：<span className={pctClass(item.yoy)}>{pctText(item.yoy)}</span>
      </div>
      <div>
        月增率：<span className={pctClass(item.mom)}>{pctText(item.mom)}</span>
      </div>
    </div>
  );
}

export function MonthlyRevenuePanel({ data }: { data: P11MonthlyRevenueResponse | undefined }) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null);

  const items = data?.items ?? [];
  const noData = data !== undefined && items.length === 0;

  // Always render exactly SPARKLINE_BARS bars; pad with nulls on the left if fewer months available.
  const paddedItems: (P11MonthlyRevenueItem | null)[] =
    items.length >= SPARKLINE_BARS
      ? items.slice(-SPARKLINE_BARS)
      : [...Array.from({ length: SPARKLINE_BARS - items.length }, () => null), ...items];

  const values = paddedItems.map((item) => item?.revenue ?? 0);
  const max = values.length > 0 ? Math.max(...values, 1) : 1;
  const latest = items[items.length - 1];

  const hoveredItem = hoveredIdx !== null ? (paddedItems[hoveredIdx] ?? null) : null;
  // Right half (last 6 bars): tooltip appears on the left to avoid right-edge overflow.
  const tooltipSide: "left" | "right" = hoveredIdx !== null && hoveredIdx >= SPARKLINE_BARS - 6 ? "left" : "right";

  return (
    <section className="rounded-lg border border-slate-700 bg-slate-950/40 p-3" data-testid="p11-panel-monthly-revenue">
      <div className="mb-2 flex items-center gap-1">
        <h3 className="text-sm font-semibold text-slate-100">月營收</h3>
        <HelpTooltip text={P11_TOOLTIP_TEXT.monthly_revenue} />
      </div>
      {noData ? (
        <p className="text-xs text-slate-500" data-testid="p11-monthly-revenue-unsupported">
          資料源未提供此標的月營收資料（如 ETF）
        </p>
      ) : (
        <>
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
          {/* onMouseLeave on container so tooltip stays while moving from bar to tooltip area */}
          <div
            className="relative rounded-md border border-slate-800 bg-slate-900/40 p-2"
            onMouseLeave={() => setHoveredIdx(null)}
          >
            <div className="mb-1 text-xs text-slate-400">近 12 月趨勢</div>
            {hoveredItem && <BarTooltip item={hoveredItem} side={tooltipSide} />}
            <div className="flex h-14 items-end gap-1" data-testid="p11-monthly-revenue-sparkline">
              {paddedItems.map((item, idx) => {
                const value = item?.revenue ?? 0;
                const height = Math.max(8, Math.round((value / max) * 52));
                const isLast = idx === SPARKLINE_BARS - 1;
                return (
                  <div
                    key={`${idx}-${item?.date ?? "empty"}`}
                    className={isLast ? "flex-1 rounded-t bg-sky-400" : "flex-1 rounded-t bg-slate-600"}
                    style={{ height: `${height}px` }}
                    data-testid={`revenue-bar-${idx}`}
                    onMouseEnter={() => item && setHoveredIdx(idx)}
                  />
                );
              })}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
