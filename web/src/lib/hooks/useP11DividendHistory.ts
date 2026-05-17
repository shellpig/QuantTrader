"use client";

import useSWR from "swr";
import { apiGet } from "@/lib/api-client";
import type { P11DividendHistoryResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";
const DISABLE_FETCH = USE_MOCK || process.env.NODE_ENV === "test";

export function useP11DividendHistory(symbol: string | null, market: Market, count = 5, enabled = true) {
  const key = !enabled || !symbol || market !== "tw" || DISABLE_FETCH ? null : `p11/dividend/${market}/${symbol}/${count}`;
  return useSWR<P11DividendHistoryResponse>(
    key,
    async () => {
      const endpoint = `/api/analysis/p11/dividend-history?symbol=${encodeURIComponent(symbol ?? "")}&market=${market}&count=${count}`;
      const response = await apiGet<P11DividendHistoryResponse>(endpoint);
      return response.data;
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
