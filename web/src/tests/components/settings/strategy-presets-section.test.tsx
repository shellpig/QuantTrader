// Tests for StrategyPresetsSection component (Phase 10-G-2)

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ success: mockToastSuccess, error: mockToastError, info: vi.fn(), dismiss: vi.fn() }),
}));

const mockMutate = vi.fn();
const mockUpsert = vi.fn();
const mockDelete = vi.fn();
const mockRestore = vi.fn();

const defaultMockPresets = [
  { name: "MA Cross", type: "moving_average_cross", params: { short_window: 20, long_window: 60 }, market: "tw" as const },
  { name: "RSI_14", type: "rsi", params: { period: 14, oversold: 30, overbought: 70 }, market: "us" as const },
];

let mockPresets = defaultMockPresets;

vi.mock("@/hooks/use-config", () => ({
  useStrategyPresets: () => ({
    presets: mockPresets,
    isLoading: false,
    mutate: mockMutate,
  }),
  upsertStrategyPreset: (...args: unknown[]) => mockUpsert(...args),
  deleteStrategyPreset: (...args: unknown[]) => mockDelete(...args),
  restoreStrategyDefaults: () => mockRestore(),
}));

// Mock the dialog to avoid full Radix Dialog complexity
vi.mock("@/components/settings/strategy-preset-dialog", () => ({
  StrategyPresetDialog: ({
    open,
    initialPreset,
    onClose,
    onSave,
  }: {
    open: boolean;
    initialPreset: null | { name: string; type: string; params: Record<string, number>; market?: "tw" | "us" };
    onClose: () => void;
    onSave: (p: { name: string; type: string; params: Record<string, number>; market?: "tw" | "us" }, isNew: boolean) => void;
  }) =>
    open ? (
      <div data-testid="mock-preset-dialog">
        <div data-testid="mock-dialog-mode">{initialPreset ? "edit" : "new"}</div>
        <button
          data-testid="mock-dialog-save"
          onClick={() =>
            onSave(
              initialPreset ?? {
                name: "New Strategy",
                type: "rsi",
                params: { period: 14, oversold: 30, overbought: 70 },
                market: "tw",
              },
              !initialPreset,
            )
          }
        >
          Save
        </button>
        {initialPreset ? (
          <button
            data-testid="mock-dialog-save-renamed"
            onClick={() =>
              onSave(
                {
                  name: "MA20_MA60",
                  type: initialPreset.type,
                  params: { short_window: 20, long_window: 60 },
                  market: initialPreset.market,
                },
                false,
              )
            }
          >
            Save Renamed
          </button>
        ) : null}
        <button data-testid="mock-dialog-close" onClick={onClose}>
          Close
        </button>
      </div>
    ) : null,
}));

import { StrategyPresetsSection } from "@/components/settings/strategy-presets-section";

describe("StrategyPresetsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockPresets = defaultMockPresets;
    mockMutate.mockResolvedValue(undefined);
  });

  it("renders preset list", () => {
    render(<StrategyPresetsSection />);
    expect(screen.getByTestId("preset-row-MA Cross")).toBeInTheDocument();
    expect(screen.getByTestId("preset-row-RSI_14")).toBeInTheDocument();
  });

  it("renders params summary in each row", () => {
    render(<StrategyPresetsSection />);
    expect(screen.getByTestId("preset-summary-MA Cross")).toHaveTextContent(
      "short_window=20, long_window=60",
    );
    expect(screen.getByTestId("preset-summary-RSI_14")).toHaveTextContent(
      "period=14, oversold=30, overbought=70",
    );
  });

  it("renders market badge in each row", () => {
    render(<StrategyPresetsSection />);
    expect(screen.getByTestId("preset-market-MA Cross")).toHaveTextContent("TW");
    expect(screen.getByTestId("preset-market-RSI_14")).toHaveTextContent("US");
  });

  it("opens dialog on add-preset-btn click", () => {
    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("add-preset-btn"));
    expect(screen.getByTestId("mock-preset-dialog")).toBeInTheDocument();
  });

  it("calls upsertStrategyPreset and shows new-preset toast", async () => {
    mockUpsert.mockResolvedValueOnce({ name: "New Strategy" });

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("add-preset-btn"));
    fireEvent.click(screen.getByTestId("mock-dialog-save"));

    await waitFor(() => expect(mockUpsert).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("已新增策略：New Strategy"),
    );
  });

  it("opens dialog in edit mode and updates existing preset", async () => {
    mockUpsert.mockResolvedValueOnce({ name: "MA Cross" });

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("edit-preset-MA Cross"));
    expect(screen.getByTestId("mock-dialog-mode")).toHaveTextContent("edit");

    fireEvent.click(screen.getByTestId("mock-dialog-save"));

    await waitFor(() =>
      expect(mockUpsert).toHaveBeenCalledWith({
        name: "MA Cross",
        type: "moving_average_cross",
        params: { short_window: 20, long_window: 60 },
        market: "tw",
      }),
    );
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("已更新策略：MA Cross"),
    );
  });

  it("deletes old preset name after editing a preset name", async () => {
    mockPresets = [
      {
        name: "MA20_MA50",
        type: "moving_average_cross",
        params: { short_window: 20, long_window: 50 },
        market: "tw",
      },
    ];
    mockUpsert.mockResolvedValueOnce({ name: "MA20_MA60" });
    mockDelete.mockResolvedValueOnce(undefined);

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("edit-preset-MA20_MA50"));
    fireEvent.click(screen.getByTestId("mock-dialog-save-renamed"));

    await waitFor(() =>
      expect(mockUpsert).toHaveBeenCalledWith({
        name: "MA20_MA60",
        type: "moving_average_cross",
        params: { short_window: 20, long_window: 60 },
        market: "tw",
      }),
    );
    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("MA20_MA50"));
    expect(mockMutate).toHaveBeenCalledTimes(1);
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("已更新策略：MA20_MA60"),
    );
  });

  it("calls deleteStrategyPreset and shows delete toast", async () => {
    mockDelete.mockResolvedValueOnce(undefined);

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("delete-preset-MA Cross"));

    await waitFor(() => expect(mockDelete).toHaveBeenCalledWith("MA Cross"));
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("已刪除策略：MA Cross"),
    );
  });

  it("calls restoreStrategyDefaults and shows restore toast", async () => {
    mockRestore.mockResolvedValueOnce(8);

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("restore-defaults-btn"));

    await waitFor(() => expect(mockRestore).toHaveBeenCalledTimes(1));
    await waitFor(() =>
      expect(mockToastSuccess).toHaveBeenCalledWith("已重置為預設 8 組策略"),
    );
  });

  it("shows error toast when delete fails", async () => {
    mockDelete.mockRejectedValueOnce(new Error("fail"));

    render(<StrategyPresetsSection />);
    fireEvent.click(screen.getByTestId("delete-preset-RSI_14"));

    await waitFor(() => expect(mockToastError).toHaveBeenCalledTimes(1));
  });
});
