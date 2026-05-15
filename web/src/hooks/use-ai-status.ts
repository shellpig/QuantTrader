import useSWR from "swr";
import { apiFetch } from "@/lib/api-client";

export interface AiStatus {
  available: boolean;
  reason: string;
  message: string;
}

export function useAiStatus() {
  const { data, error, isLoading } = useSWR<AiStatus>(
    "/api/ai/status",
    (url: string) => apiFetch<AiStatus>(url),
    { refreshInterval: 0 },
  );
  return {
    status: data,
    isLoading,
    isError: !!error,
  };
}
