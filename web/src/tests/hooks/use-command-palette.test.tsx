import { render, waitFor } from "@testing-library/react";
import { renderHook } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

describe("use-command-palette store", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it("registers and unregisters entry by lifecycle", async () => {
    const mod = await import("@/hooks/use-command-palette");

    function MountEntry() {
      mod.useCommandPaletteEntry({
        id: "nav-dashboard",
        label: "個股分析",
        group: "pages",
        action: () => undefined,
      });
      return null;
    }

    const probe = renderHook(() => mod.useCommandEntries());
    expect(probe.result.current).toHaveLength(0);

    const ui = render(<MountEntry />);
    await waitFor(() => {
      expect(probe.result.current).toHaveLength(1);
    });

    ui.unmount();
    await waitFor(() => {
      expect(probe.result.current).toHaveLength(0);
    });
  });

  it("dedupes entries by id", async () => {
    const mod = await import("@/hooks/use-command-palette");

    function EntryA() {
      mod.useCommandPaletteEntry({
        id: "same-id",
        label: "A",
        group: "pages",
        action: () => undefined,
      });
      return null;
    }
    function EntryB() {
      mod.useCommandPaletteEntry({
        id: "same-id",
        label: "B",
        group: "pages",
        action: () => undefined,
      });
      return null;
    }

    render(
      <>
        <EntryA />
        <EntryB />
      </>,
    );

    const probe = renderHook(() => mod.useCommandEntries());
    await waitFor(() => {
      expect(probe.result.current).toHaveLength(1);
    });
  });

  it("shares one store and tracks latest stock market source", async () => {
    const mod = await import("@/hooks/use-command-palette");

    function SourceA() {
      mod.useCommandPaletteStockSource("tw");
      return null;
    }
    function SourceB() {
      mod.useCommandPaletteStockSource("us");
      return null;
    }

    render(
      <>
        <SourceA />
        <SourceB />
      </>,
    );

    const marketProbe = renderHook(() => mod.useCommandPaletteStockMarket());
    await waitFor(() => {
      expect(marketProbe.result.current).toBe("us");
    });
  });
});
