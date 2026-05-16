// Tests for StrategyPresetDialog component (Phase 10-G-2)

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { StrategyPresetDialog } from "@/components/settings/strategy-preset-dialog";

// Radix Dialog uses portals — jsdom needs this
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

const mockOnSave = vi.fn();
const mockOnClose = vi.fn();

function renderDialog(open = true, initialPreset = null as null | { name: string; type: string; params: Record<string, number> }) {
  return render(
    <StrategyPresetDialog
      open={open}
      initialPreset={initialPreset}
      onClose={mockOnClose}
      onSave={mockOnSave}
    />,
  );
}

describe("StrategyPresetDialog", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders dialog with name input and type select when open", () => {
    renderDialog();
    expect(screen.getByTestId("preset-dialog")).toBeInTheDocument();
    expect(screen.getByTestId("preset-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("preset-type-select")).toBeInTheDocument();
  });

  it("does not render when closed", () => {
    renderDialog(false);
    expect(screen.queryByTestId("preset-dialog")).not.toBeInTheDocument();
  });

  it("submit button is disabled when name is empty", () => {
    renderDialog();
    const submitBtn = screen.getByTestId("preset-dialog-submit");
    expect(submitBtn).toBeDisabled();
  });

  it("submit button is enabled after entering a name", () => {
    renderDialog();
    fireEvent.change(screen.getByTestId("preset-name-input"), {
      target: { value: "My MA" },
    });
    expect(screen.getByTestId("preset-dialog-submit")).not.toBeDisabled();
  });

  it("calls onSave with correct preset on submit", () => {
    renderDialog();
    fireEvent.change(screen.getByTestId("preset-name-input"), {
      target: { value: "My MA" },
    });
    fireEvent.click(screen.getByTestId("preset-dialog-submit"));
    expect(mockOnSave).toHaveBeenCalledWith(
      expect.objectContaining({ name: "My MA", type: "moving_average_cross" }),
      true, // isNew
    );
  });

  it("changing type updates visible param fields", () => {
    renderDialog();
    fireEvent.change(screen.getByTestId("preset-type-select"), {
      target: { value: "rsi" },
    });
    expect(screen.getByTestId("param-period")).toBeInTheDocument();
    expect(screen.getByTestId("param-oversold")).toBeInTheDocument();
    expect(screen.getByTestId("param-overbought")).toBeInTheDocument();
    expect(screen.queryByTestId("param-short_window")).not.toBeInTheDocument();
  });

  it("shows eight strategy options including dollar_cost_averaging", () => {
    renderDialog();
    const select = screen.getByTestId("preset-type-select") as HTMLSelectElement;
    expect(select.options).toHaveLength(8);
    expect(
      Array.from(select.options).some(
        (option) => option.value === "dollar_cost_averaging",
      ),
    ).toBe(true);
  });

  it("shows monthly_day and monthly_amount fields for DCA type", () => {
    renderDialog();
    fireEvent.change(screen.getByTestId("preset-type-select"), {
      target: { value: "dollar_cost_averaging" },
    });

    expect(screen.getByTestId("param-monthly_day")).toBeInTheDocument();
    expect(screen.getByTestId("param-monthly_amount")).toBeInTheDocument();
    expect(screen.queryByTestId("param-short_window")).not.toBeInTheDocument();
  });

  it("pre-fills form when editing existing preset", () => {
    renderDialog(true, {
      name: "Existing RSI",
      type: "rsi",
      params: { period: 21, oversold: 25, overbought: 75 },
    });
    const nameInput = screen.getByTestId("preset-name-input") as HTMLInputElement;
    expect(nameInput.value).toBe("Existing RSI");
    const periodInput = screen.getByTestId("param-period") as HTMLInputElement;
    expect(periodInput.value).toBe("21");
  });

  it("calls onClose when cancel button clicked", () => {
    renderDialog();
    fireEvent.click(screen.getByTestId("preset-dialog-cancel"));
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });
});
