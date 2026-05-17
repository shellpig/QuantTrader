"use client";

import useSWR from "swr";
import { apiGet } from "@/lib/api-client";
import type { P11IndustryPerResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";
const DISABLE_FETCH = USE_MOCK || process.env.NODE_ENV === "test";

export function useP11IndustryPer(symbol: string | null, market: Market, enabled = false) {
  const key = !enabled || !symbol || market !== "tw" || DISABLE_FETCH ? null : `p11/industry/${market}/${symbol}`;
  return useSWR<P11IndustryPerResponse>(
    key,
    async () => {
      const endpoint = `/api/analysis/p11/industry-per?symbol=${encodeURIComponent(symbol ?? "")}&market=${market}`;
      const response = await apiGet<P11IndustryPerResponse>(endpoint);
      return response.data;
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
