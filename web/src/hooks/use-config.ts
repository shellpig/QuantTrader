"use client";

import useSWR from "swr";
import { apiFetch, apiPut, apiPost, apiDeleteNoContent } from "@/lib/api-client";

export interface StrategyPreset {
  name: string;
  type: string;
  params: Record<string, number>;
}

export const SECRETS_SWR_KEY = "/api/config/secrets/status";
export const STRATEGIES_SWR_KEY = "/api/config/strategies";

export function useSecretsStatus() {
  const { data, error, isLoading, mutate } = useSWR<Record<string, boolean>>(
    SECRETS_SWR_KEY,
    async (url: string) => {
      const res = await apiFetch<{ data: Record<string, boolean> }>(url);
      return res.data;
    },
  );
  return { status: data ?? {}, isLoading, isError: !!error, mutate };
}

export function useStrategyPresets() {
  const { data, error, isLoading, mutate } = useSWR<StrategyPreset[]>(
    STRATEGIES_SWR_KEY,
    async (url: string) => {
      const res = await apiFetch<{ data: StrategyPreset[] }>(url);
      return res.data;
    },
  );
  return { presets: data ?? [], isLoading, isError: !!error, mutate };
}

export async function updateSecrets(keys: Record<string, string>): Promise<void> {
  await apiPut("/api/config/secrets", { keys });
}

export async function upsertStrategyPreset(
  preset: StrategyPreset,
): Promise<{ name: string }> {
  const res = await apiPost<{ upserted: boolean; name: string }>(
    "/api/config/strategies",
    { preset },
  );
  return { name: res.data.name };
}

export async function deleteStrategyPreset(name: string): Promise<void> {
  await apiDeleteNoContent(`/api/config/strategies/${encodeURIComponent(name)}`);
}

export async function restoreStrategyDefaults(): Promise<number> {
  const res = await apiPost<{ count: number }>(
    "/api/config/strategies/restore",
    {},
  );
  return res.data.count;
}
