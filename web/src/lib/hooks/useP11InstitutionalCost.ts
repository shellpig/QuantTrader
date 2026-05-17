"use client";

import useSWR from "swr";
import { apiGet } from "@/lib/api-client";
import type { P11InstitutionalCostResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";
const DISABLE_FETCH = USE_MOCK || process.env.NODE_ENV === "test";

export function useP11InstitutionalCost(symbol: string | null, market: Market, days = 30, enabled = true) {
  const key = !enabled || !symbol || market !== "tw" || DISABLE_FETCH ? null : `p11/institutional-cost/${market}/${symbol}/${days}`;
  return useSWR<P11InstitutionalCostResponse>(
    key,
    async () => {
      const endpoint = `/api/analysis/p11/institutional-cost?symbol=${encodeURIComponent(symbol ?? "")}&market=${market}&days=${days}`;
      const response = await apiGet<P11InstitutionalCostResponse>(endpoint);
      return response.data;
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
