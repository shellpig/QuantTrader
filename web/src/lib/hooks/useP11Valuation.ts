"use client";

import useSWR from "swr";
import { apiGet } from "@/lib/api-client";
import type { P11ValuationResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";
const DISABLE_FETCH = USE_MOCK || process.env.NODE_ENV === "test";

export function useP11Valuation(symbol: string | null, market: Market, enabled = true) {
  const key = !enabled || !symbol || market !== "tw" || DISABLE_FETCH ? null : `p11/valuation/${market}/${symbol}`;
  return useSWR<P11ValuationResponse>(
    key,
    async () => {
      const endpoint = `/api/analysis/p11/valuation?symbol=${encodeURIComponent(symbol ?? "")}&market=${market}`;
      const response = await apiGet<P11ValuationResponse>(endpoint);
      return response.data;
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
