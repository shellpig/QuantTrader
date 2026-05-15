"use client";

import { useEffect, useMemo, useRef, useSyncExternalStore } from "react";
import type { Market } from "@/types/market";

export type CommandEntryGroup = "pages" | "stocks";

export type CommandEntry = {
  id: string;
  label: string;
  group?: CommandEntryGroup;
  action: () => void;
};

type CommandState = {
  entries: CommandEntry[];
  stockMarket: Market;
};

let entries: CommandEntry[] = [];
const stockSources = new Map<symbol, Market>();
const listeners = new Set<() => void>();
let snapshot: CommandState = {
  entries: [],
  stockMarket: "tw",
};

function emit() {
  snapshot = {
    entries,
    stockMarket: getCurrentStockMarket(),
  };
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void) {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function getCurrentStockMarket(): Market {
  let current: Market = "tw";
  for (const value of stockSources.values()) {
    current = value;
  }
  return current;
}

function getSnapshot(): CommandState {
  return snapshot;
}

export function useCommandStore() {
  return useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

export function useCommandEntries() {
  const state = useCommandStore();
  return state.entries;
}

export function useCommandPaletteStockMarket() {
  const state = useCommandStore();
  return state.stockMarket;
}

export function useCommandPaletteEntry(entry: CommandEntry) {
  const stableEntry = useMemo(
    () => ({
      id: entry.id,
      label: entry.label,
      group: entry.group,
      action: entry.action,
    }),
    [entry.id, entry.label, entry.group, entry.action],
  );

  useEffect(() => {
    entries = [...entries.filter((item) => item.id !== stableEntry.id), stableEntry];
    emit();
    return () => {
      entries = entries.filter((item) => item.id !== stableEntry.id);
      emit();
    };
  }, [stableEntry]);
}

export function useCommandPaletteStockSource(market: Market) {
  const tokenRef = useRef(Symbol("stock-source"));

  useEffect(() => {
    const token = tokenRef.current;
    stockSources.delete(token);
    stockSources.set(token, market);
    emit();

    return () => {
      stockSources.delete(token);
      emit();
    };
  }, [market]);
}
