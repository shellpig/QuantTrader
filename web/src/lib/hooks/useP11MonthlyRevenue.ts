"use client";

import useSWR from "swr";
import { apiGet } from "@/lib/api-client";
import type { P11MonthlyRevenueResponse } from "@/types/analysis";
import type { Market } from "@/types/market";

const USE_MOCK = process.env.NEXT_PUBLIC_USE_MOCK_DASHBOARD === "1";
const DISABLE_FETCH = USE_MOCK || process.env.NODE_ENV === "test";

export function useP11MonthlyRevenue(symbol: string | null, market: Market, months = 12) {
  const key = !symbol || market !== "tw" || DISABLE_FETCH ? null : `p11/monthly/${market}/${symbol}/${months}`;
  return useSWR<P11MonthlyRevenueResponse>(
    key,
    async () => {
      const endpoint = `/api/analysis/p11/monthly-revenue?symbol=${encodeURIComponent(symbol ?? "")}&market=${market}&months=${months}`;
      const response = await apiGet<P11MonthlyRevenueResponse>(endpoint);
      return response.data;
    },
    { revalidateOnFocus: false, dedupingInterval: 30_000 },
  );
}
