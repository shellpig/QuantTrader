// Tests for DataTable component (Phase 10-C-bug)
// Covers: name display, symbol fallback, empty state

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { DataTable } from "@/components/data/DataTable";
import type { SymbolRow } from "@/types/data";

function makeRow(overrides: Partial<SymbolRow> = {}): SymbolRow {
  return {
    symbol: "2330",
    market: "tw",
    name: undefined,
    firstDate: "2020-01-02",
    lastDate: "2026-05-14",
    bars: 1500,
    status: "fresh",
    hasAdjusted: true,
    ...overrides,
  };
}

describe("DataTable", () => {
  it("shows empty state when rows is empty", () => {
    render(<DataTable rows={[]} onDelete={vi.fn()} />);
    expect(screen.getByText(/目前沒有本機資料/)).toBeInTheDocument();
  });

  it("renders a row for each symbol", () => {
    const rows = [makeRow({ symbol: "2330" }), makeRow({ symbol: "0050" })];
    render(<DataTable rows={rows} onDelete={vi.fn()} />);
    expect(screen.getByTestId("data-row-2330")).toBeInTheDocument();
    expect(screen.getByTestId("data-row-0050")).toBeInTheDocument();
  });

  it("shows name when provided (Bug 2 fix)", () => {
    const rows = [makeRow({ symbol: "0050", name: "元大台灣50" })];
    render(<DataTable rows={rows} onDelete={vi.fn()} />);
    expect(screen.getByText("元大台灣50")).toBeInTheDocument();
  });

  it("falls back to symbol when name is undefined (Bug 2 fallback)", () => {
    const rows = [makeRow({ symbol: "2330", name: undefined })];
    render(<DataTable rows={rows} onDelete={vi.fn()} />);
    // symbol column shows "2330"; name column also falls back to "2330"
    const cells = screen.getAllByText("2330");
    expect(cells.length).toBeGreaterThanOrEqual(2); // code col + name col
  });

  it("shows raw+adj badge for US market rows", () => {
    const rows = [makeRow({ symbol: "AAPL", market: "us", name: undefined })];
    render(<DataTable rows={rows} onDelete={vi.fn()} />);
    expect(screen.getByText("raw+adj")).toBeInTheDocument();
  });

  it("does not show raw+adj badge for TW market rows", () => {
    const rows = [makeRow({ symbol: "2330", market: "tw" })];
    render(<DataTable rows={rows} onDelete={vi.fn()} />);
    expect(screen.queryByText("raw+adj")).not.toBeInTheDocument();
  });
});
