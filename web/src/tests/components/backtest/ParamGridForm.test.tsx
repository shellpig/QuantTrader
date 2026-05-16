import { useState } from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { Market } from "@/types/market";
import type { SweepStrategyType } from "@/components/backtest/sweep-types";
import { ParamGridForm } from "@/components/backtest/ParamGridForm";
import { createDefaultParamInputs } from "@/components/backtest/sweep-helpers";

vi.mock("@/components/market-switcher", () => ({
  MarketSwitcher: ({ value, onChange }: { value: string; onChange: (m: Market) => void }) => (
    <button type="button" data-testid="mock-market" onClick={() => onChange(value === "tw" ? "us" : "tw")}>
      market
    </button>
  ),
}));

vi.mock("@/components/stock-selector", () => ({
  StockSelector: ({ value, onChange }: { value: string; onChange: (v: string) => void }) => (
    <input data-testid="mock-stock" value={value} onChange={(e) => onChange(e.target.value)} />
  ),
}));

function Harness({
  onSubmit = vi.fn(),
}: {
  onSubmit?: (payload: unknown) => void;
}) {
  const [market, setMarket] = useState<Market>("tw");
  const [symbol, setSymbol] = useState("");
  const [startDate, setStartDate] = useState("2020-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [strategyType, setStrategyType] = useState<SweepStrategyType>("moving_average_cross");
  const [paramInputs, setParamInputs] = useState(createDefaultParamInputs("moving_average_cross"));
  const [initialCapital, setInitialCapital] = useState(1_000_000);

  return (
    <ParamGridForm
      market={market}
      symbol={symbol}
      startDate={startDate}
      endDate={endDate}
      strategyType={strategyType}
      paramInputs={paramInputs}
      initialCapital={initialCapital}
      onMarketChange={setMarket}
      onSymbolChange={setSymbol}
      onStartDateChange={setStartDate}
      onEndDateChange={setEndDate}
      onStrategyTypeChange={(next) => {
        setStrategyType(next);
        setParamInputs(createDefaultParamInputs(next));
      }}
      onParamInputChange={(k, v) => setParamInputs((prev) => ({ ...prev, [k]: v }))}
      onInitialCapitalChange={setInitialCapital}
      onSubmit={onSubmit as any}
    />
  );
}

describe("ParamGridForm", () => {
  it("loads default MA crossover inputs", () => {
    render(<Harness />);
    expect(screen.getByTestId("param-input-short_window")).toHaveValue("5,10,20");
    expect(screen.getByTestId("param-input-long_window")).toHaveValue("40,60,120");
    expect(screen.getByTestId("sweep-combo-summary")).toHaveTextContent("總組合數 9 / 合法組合數 9 / 上限 200");
  });

  it("switches param inputs by strategy type", () => {
    render(<Harness />);
    fireEvent.change(screen.getByTestId("sweep-strategy-type"), {
      target: { value: "rsi" },
    });
    expect(screen.getByTestId("param-input-period")).toBeInTheDocument();
    expect(screen.getByTestId("param-input-oversold")).toBeInTheDocument();
    expect(screen.getByTestId("param-input-overbought")).toBeInTheDocument();
  });

  it("shows parse error for invalid comma list", () => {
    render(<Harness />);
    fireEvent.change(screen.getByTestId("param-input-short_window"), {
      target: { value: "abc,10" },
    });
    expect(screen.getByTestId("sweep-parse-error")).toBeInTheDocument();
    expect(screen.getByTestId("start-sweep-btn")).toBeDisabled();
  });

  it("rejects decimal for integer-only param", () => {
    render(<Harness />);
    fireEvent.change(screen.getByTestId("param-input-short_window"), {
      target: { value: "5.5,10" },
    });
    expect(screen.getByTestId("sweep-parse-error")).toBeInTheDocument();
    expect(screen.getByTestId("start-sweep-btn")).toBeDisabled();
  });

  it("shows over-limit warning when valid combos exceed 200", () => {
    render(<Harness />);
    fireEvent.change(screen.getByTestId("param-input-short_window"), {
      target: { value: "1,2,3,4,5,6,7,8,9,10,11,12,13,14,15" },
    });
    fireEvent.change(screen.getByTestId("param-input-long_window"), {
      target: { value: "16,17,18,19,20,21,22,23,24,25,26,27,28,29,30" },
    });
    expect(screen.getByTestId("sweep-over-limit")).toBeInTheDocument();
    expect(screen.getByTestId("start-sweep-btn")).toBeDisabled();
  });

  it("submits parsed candidate lists", () => {
    const onSubmit = vi.fn();
    render(<Harness onSubmit={onSubmit} />);
    fireEvent.change(screen.getByTestId("mock-stock"), {
      target: { value: "2330" },
    });
    fireEvent.change(screen.getByTestId("param-input-short_window"), {
      target: { value: "20,5,10,10" },
    });
    fireEvent.change(screen.getByTestId("param-input-long_window"), {
      target: { value: "40,60" },
    });
    fireEvent.click(screen.getByTestId("start-sweep-btn"));

    expect(onSubmit).toHaveBeenCalledTimes(1);
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      strategy_type: "moving_average_cross",
      param_candidates: {
        short_window: [5, 10, 20],
        long_window: [40, 60],
      },
      total_combos: 6,
      valid_combos: 6,
    });
  });
});
