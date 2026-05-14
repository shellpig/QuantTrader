// Market types (Phase 10-B)

export type Market = "tw" | "us";

export const MARKET_LABELS: Record<Market, string> = {
  tw: "台股",
  us: "美股",
};

export const MARKET_CURRENCY: Record<Market, string> = {
  tw: "TWD",
  us: "USD",
};

/** Chart candle colour convention per market. */
export const MARKET_UP_COLOR: Record<Market, string> = {
  tw: "#ef4444",  // red = rise (台股)
  us: "#22c55e",  // green = rise (US)
};

export const MARKET_DOWN_COLOR: Record<Market, string> = {
  tw: "#22c55e",  // green = fall (台股)
  us: "#ef4444",  // red = fall (US)
};
