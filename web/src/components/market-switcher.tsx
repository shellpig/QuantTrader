"use client";

// Market Switcher component (Phase 10-B)

import { MARKET_LABELS } from "@/types/market";
import type { Market } from "@/types/market";
import { cn } from "@/lib/utils";

interface MarketSwitcherProps {
  value: Market;
  onChange: (market: Market) => void;
  className?: string;
}

export function MarketSwitcher({
  value,
  onChange,
  className,
}: MarketSwitcherProps) {
  const markets: Market[] = ["tw", "us"];

  return (
    <div
      className={cn(
        "inline-flex rounded-lg border border-border bg-muted p-0.5",
        className,
      )}
      role="group"
      aria-label="市場切換"
      data-testid="market-switcher"
    >
      {markets.map((market) => (
        <button
          key={market}
          type="button"
          onClick={() => onChange(market)}
          className={cn(
            "rounded-md px-3 py-1 text-sm font-medium transition-colors",
            value === market
              ? "bg-background text-foreground shadow-sm"
              : "text-muted-foreground hover:text-foreground",
          )}
          aria-pressed={value === market}
          data-testid={`market-option-${market}`}
        >
          {MARKET_LABELS[market]}
        </button>
      ))}
    </div>
  );
}
