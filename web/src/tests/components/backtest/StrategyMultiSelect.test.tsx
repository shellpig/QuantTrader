import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { StrategyMultiSelect } from "@/components/backtest/StrategyMultiSelect";

const PRESETS = [
  { name: "MA20_MA60", type: "moving_average_cross", params: {} },
  { name: "RSI_14", type: "rsi", params: {} },
  { name: "KD_Cross", type: "kd_cross", params: {} },
];

describe("StrategyMultiSelect", () => {
  it("renders all preset checkboxes", () => {
    render(
      <StrategyMultiSelect
        presets={PRESETS}
        selectedIndices={[0, 1, 2]}
        onChange={() => {}}
      />,
    );
    expect(screen.getByTestId("strategy-option-0")).toBeInTheDocument();
    expect(screen.getByTestId("strategy-option-1")).toBeInTheDocument();
    expect(screen.getByTestId("strategy-option-2")).toBeInTheDocument();
  });

  it("toggles one preset off", () => {
    const onChange = vi.fn();
    render(
      <StrategyMultiSelect
        presets={PRESETS}
        selectedIndices={[0, 1, 2]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("strategy-option-1"));
    expect(onChange).toHaveBeenCalledWith([0, 2]);
  });

  it("toggles one preset on", () => {
    const onChange = vi.fn();
    render(
      <StrategyMultiSelect
        presets={PRESETS}
        selectedIndices={[0, 2]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("strategy-option-1"));
    expect(onChange).toHaveBeenCalledWith([0, 1, 2]);
  });

  it("select-all checks all presets", () => {
    const onChange = vi.fn();
    render(
      <StrategyMultiSelect
        presets={PRESETS}
        selectedIndices={[]}
        onChange={onChange}
      />,
    );
    fireEvent.click(screen.getByTestId("strategy-select-all"));
    expect(onChange).toHaveBeenCalledWith([0, 1, 2]);
  });

  it("disabled state blocks changes", () => {
    const onChange = vi.fn();
    render(
      <StrategyMultiSelect
        presets={PRESETS}
        selectedIndices={[0, 1, 2]}
        onChange={onChange}
        disabled
      />,
    );
    fireEvent.click(screen.getByTestId("strategy-option-1"));
    expect(onChange).not.toHaveBeenCalled();
  });
});

