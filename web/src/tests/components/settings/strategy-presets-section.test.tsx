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

let mockPresets = [
  { name: "MA Cross", type: "moving_average_cross", params: { short_window: 20, long_window: 60 } },
  { name: "RSI_14", type: "rsi", params: { period: 14, oversold: 30, overbought: 70 } },
];

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
    onClose,
    onSave,
  }: {
    open: boolean;
    onClose: () => void;
    onSave: (p: { name: string; type: string; params: Record<string, number> }, isNew: boolean) => void;
  }) =>
    open ? (
      <div data-testid="mock-preset-dialog">
        <button
          data-testid="mock-dialog-save"
          onClick={() =>
            onSave(
              { name: "New Strategy", type: "rsi", params: { period: 14, oversold: 30, overbought: 70 } },
              true,
            )
          }
        >
          Save
        </button>
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
    mockMutate.mockResolvedValue(undefined);
  });

  it("renders preset list", () => {
    render(<StrategyPresetsSection />);
    expect(screen.getByTestId("preset-row-MA Cross")).toBeInTheDocument();
    expect(screen.getByTestId("preset-row-RSI_14")).toBeInTheDocument();
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
