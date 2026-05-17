import { useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { ArrowDown, ArrowUp, X } from "lucide-react";
import { HelpTooltip } from "@/components/dashboard/help-tooltip";
import { P11_TOOLTIP_TEXT } from "@/components/dashboard/tooltip-text";
import { formatNumber } from "@/lib/formatters";
import type { P11IndustryPerResponse } from "@/types/analysis";

type SortKey = "symbol" | "name" | "per" | "pbr" | "dividend_yield";

function renderNumber(value: number | null, digits = 2): string {
  if (value == null || Number.isNaN(value)) return "—";
  return formatNumber(value, digits);
}

export function IndustryPerModal({
  open,
  onOpenChange,
  data,
  isLoading,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  data: P11IndustryPerResponse | undefined;
  isLoading: boolean;
}) {
  const [sortKey, setSortKey] = useState<SortKey>("per");
  const [sortDesc, setSortDesc] = useState(true);

  const rows = useMemo(() => {
    const items = [...(data?.items ?? [])];
    items.sort((a, b) => {
      const av = a[sortKey];
      const bv = b[sortKey];
      const aValue = av == null ? "" : av;
      const bValue = bv == null ? "" : bv;
      let base = 0;
      if (typeof aValue === "number" && typeof bValue === "number") {
        base = aValue === bValue ? 0 : aValue > bValue ? 1 : -1;
      } else {
        base = String(aValue).localeCompare(String(bValue), "zh-Hant");
      }
      return sortDesc ? -base : base;
    });
    return items;
  }, [data?.items, sortDesc, sortKey]);

  const toggleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDesc((prev) => !prev);
      return;
    }
    setSortKey(key);
    setSortDesc(true);
  };

  const sortIcon = sortDesc ? <ArrowDown className="h-3.5 w-3.5" /> : <ArrowUp className="h-3.5 w-3.5" />;

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-40 bg-black/70" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 h-[90vh] w-[96vw] max-w-[1800px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-950 p-4 text-slate-100">
          <div className="mb-3 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold">
              同產業本益比 {data?.industry ? `· ${data.industry}` : ""}
            </Dialog.Title>
            <Dialog.Close asChild>
              <button type="button" className="rounded-md border border-slate-700 p-1 hover:bg-slate-800" aria-label="關閉">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>
          <Dialog.Description className="mb-3 text-xs text-slate-400">
            顯示同產業估值快照，支援欄位排序，黃色列為目前分析標的。
          </Dialog.Description>

          <div className="mb-2 flex flex-wrap items-center gap-4 rounded-md border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs">
            <div className="text-slate-400">
              中位數：<span className="text-slate-100 [font-family:var(--font-mono)]">{renderNumber(data?.median ?? null)}</span>
            </div>
            <div className="text-slate-400">
              平均數：<span className="text-slate-100 [font-family:var(--font-mono)]">{renderNumber(data?.mean ?? null)}</span>
            </div>
            <div className="text-slate-400">
              樣本數：<span className="text-slate-100 [font-family:var(--font-mono)]">{data?.count ?? 0}</span>
            </div>
            <div className="text-slate-500">快取時間：{data?.cached_at ?? "—"}</div>
          </div>

          <div className="relative h-[calc(90vh-134px)] overflow-hidden rounded-lg border border-slate-800 bg-slate-900/30">
            <div className="h-full overflow-auto">
              <table className="w-full text-sm">
                <thead className="sticky top-0 z-20 bg-slate-900/95 text-slate-300">
                  <tr>
                    <th className="px-3 py-2 text-left">
                      <button type="button" className="inline-flex items-center gap-1" onClick={() => toggleSort("symbol")}>
                        代碼 {sortKey === "symbol" ? sortIcon : null}
                      </button>
                    </th>
                    <th className="px-3 py-2 text-left">
                      <button type="button" className="inline-flex items-center gap-1" onClick={() => toggleSort("name")}>
                        名稱 {sortKey === "name" ? sortIcon : null}
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right">
                      <button type="button" className="inline-flex items-center gap-1" onClick={() => toggleSort("per")}>
                        本益比
                        <HelpTooltip text={P11_TOOLTIP_TEXT.per_abbr} />
                        {sortKey === "per" ? sortIcon : null}
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right">
                      <button type="button" className="inline-flex items-center gap-1" onClick={() => toggleSort("pbr")}>
                        股價淨值比
                        <HelpTooltip text={P11_TOOLTIP_TEXT.pbr} />
                        {sortKey === "pbr" ? sortIcon : null}
                      </button>
                    </th>
                    <th className="px-3 py-2 text-right">
                      <button type="button" className="inline-flex items-center gap-1" onClick={() => toggleSort("dividend_yield")}>
                        殖利率 {sortKey === "dividend_yield" ? sortIcon : null}
                      </button>
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {(rows.length > 0 ? rows : Array.from({ length: 8 }, () => null)).map((row, idx) => (
                    <tr
                      key={`${row?.symbol ?? "skeleton"}-${idx}`}
                      className={`border-t border-slate-800 ${row?.is_current ? "bg-amber-500/15" : ""}`}
                    >
                      <td className="px-3 py-2 [font-family:var(--font-mono)]">{row?.symbol ?? "—"}</td>
                      <td className="px-3 py-2">
                        {row?.name ?? "—"} {row?.is_current ? <span className="text-amber-300">← 當前</span> : null}
                      </td>
                      <td className="px-3 py-2 text-right [font-family:var(--font-mono)]">{row ? renderNumber(row.per) : "—"}</td>
                      <td className="px-3 py-2 text-right [font-family:var(--font-mono)]">{row ? renderNumber(row.pbr) : "—"}</td>
                      <td className="px-3 py-2 text-right [font-family:var(--font-mono)]">
                        {row ? (row.dividend_yield == null ? "—" : `${renderNumber(row.dividend_yield)}%`) : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {isLoading ? (
              <div className="absolute inset-0 z-10 flex items-center justify-center bg-slate-950/55 backdrop-blur-[1px]">
                <div className="rounded-lg border border-slate-700 bg-slate-900 px-5 py-4 text-center shadow-xl">
                  <p className="text-sm font-semibold text-slate-100">資料讀取中，正在整理同產業本益比...</p>
                  <p className="mt-1 text-xs text-slate-400">首次載入約 8-25 秒，完成後會一次更新</p>
                </div>
              </div>
            ) : null}
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
