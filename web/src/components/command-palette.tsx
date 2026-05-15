"use client";

import { Command } from "cmdk";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { apiFetch } from "@/lib/api-client";
import {
  useCommandEntries,
  useCommandPaletteStockMarket,
  type CommandEntry,
} from "@/hooks/use-command-palette";

type SymbolRecord = {
  symbol: string;
  name?: string;
};

const STOCK_RESULT_LIMIT = 10;
const SEARCH_DEBOUNCE_MS = 200;

function buildStockLabel(row: SymbolRecord) {
  return row.name && row.name !== row.symbol
    ? `${row.symbol} ${row.name}`
    : row.symbol;
}

export function CommandPalette() {
  const router = useRouter();
  const entries = useCommandEntries();
  const stockMarket = useCommandPaletteStockMarket();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [stockEntries, setStockEntries] = useState<CommandEntry[]>([]);

  const pageEntries = useMemo(
    () => entries.filter((entry) => (entry.group ?? "pages") === "pages"),
    [entries],
  );

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.key === "k" || event.key === "K") && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        setOpen((prev) => !prev);
        return;
      }

      if (event.key === "/") {
        const target = event.target as HTMLElement | null;
        const tag = target?.tagName;
        const isEditable = target?.isContentEditable;
        if (isEditable || tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") {
          return;
        }
        event.preventDefault();
        setOpen(true);
        return;
      }

      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  useEffect(() => {
    if (!open) {
      setQuery("");
      setStockEntries((prev) => (prev.length === 0 ? prev : []));
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const trimmed = query.trim();
    if (!trimmed) {
      setStockEntries((prev) => (prev.length === 0 ? prev : []));
      return;
    }

    let cancelled = false;
    const timer = window.setTimeout(async () => {
      try {
        const response = await apiFetch<{
          data: Array<SymbolRecord | string>;
          meta: { market: string; count: number };
        }>(`/api/data/symbols?market=${stockMarket}&q=${encodeURIComponent(trimmed)}`);

        if (cancelled) return;
        const normalized = response.data.map((row) =>
          typeof row === "string" ? ({ symbol: row } as SymbolRecord) : row,
        );
        const lower = trimmed.toLowerCase();
        const filtered = normalized
          .filter((row) => {
            const symbol = row.symbol.toLowerCase();
            const name = row.name?.toLowerCase() ?? "";
            return symbol.includes(lower) || name.includes(lower);
          })
          .slice(0, STOCK_RESULT_LIMIT);

        const mapped: CommandEntry[] = filtered.map((row) => ({
          id: `stock-${stockMarket}-${row.symbol}`,
          label: buildStockLabel(row),
          group: "stocks",
          action: () => {
            router.push(`/dashboard?symbol=${encodeURIComponent(row.symbol)}`);
          },
        }));
        setStockEntries(mapped);
      } catch {
        if (!cancelled) {
          setStockEntries([]);
        }
      }
    }, SEARCH_DEBOUNCE_MS);

    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [open, query, router, stockMarket]);

  const hasResults = pageEntries.length > 0 || stockEntries.length > 0;

  function handleSelect(entry: CommandEntry) {
    entry.action();
    setOpen(false);
  }

  return (
    <Command.Dialog
      open={open}
      onOpenChange={setOpen}
      label="全域指令"
      className="fixed left-1/2 top-24 z-50 w-[calc(100%-2rem)] max-w-xl -translate-x-1/2 overflow-hidden rounded-lg border border-border bg-card shadow-2xl"
      overlayClassName="fixed inset-0 z-40 bg-black/40"
    >
      <Command.Input
        value={query}
        onValueChange={setQuery}
        autoFocus
        placeholder="輸入頁面名稱或股票代碼..."
        className="w-full border-b border-border bg-transparent px-3 py-3 text-sm text-foreground outline-none placeholder:text-muted-foreground"
      />
      <Command.List className="max-h-80 overflow-y-auto p-2">
        {!hasResults && <Command.Empty>找不到結果</Command.Empty>}

        {pageEntries.length > 0 && (
          <Command.Group heading="頁面">
            {pageEntries.map((entry) => (
              <Command.Item
                key={entry.id}
                value={`${entry.label} ${entry.id}`}
                onSelect={() => handleSelect(entry)}
                className="cursor-pointer rounded px-2 py-2 text-sm text-foreground aria-selected:bg-muted"
              >
                {entry.label}
              </Command.Item>
            ))}
          </Command.Group>
        )}

        {stockEntries.length > 0 && (
          <Command.Group heading={`股票（${stockMarket.toUpperCase()}）`}>
            {stockEntries.map((entry) => (
              <Command.Item
                key={entry.id}
                value={`${entry.label} ${entry.id}`}
                onSelect={() => handleSelect(entry)}
                className="cursor-pointer rounded px-2 py-2 text-sm text-foreground aria-selected:bg-muted"
              >
                {entry.label}
              </Command.Item>
            ))}
          </Command.Group>
        )}
      </Command.List>
    </Command.Dialog>
  );
}
