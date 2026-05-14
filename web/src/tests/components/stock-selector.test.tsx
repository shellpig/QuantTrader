// Tests for StockSelector component (Phase 10-B)

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { StockSelector } from "@/components/stock-selector";

describe("StockSelector", () => {
  it("renders with TW placeholder by default", () => {
    render(
      <StockSelector market="tw" value="" onChange={() => undefined} />,
    );
    const input = screen.getByTestId("stock-selector-input");
    expect(input).toHaveAttribute(
      "placeholder",
      "股票代碼或名稱（Enter 送出）",
    );
  });

  it("renders with US placeholder for market=us", () => {
    render(
      <StockSelector market="us" value="" onChange={() => undefined} />,
    );
    const input = screen.getByTestId("stock-selector-input");
    expect(input).toHaveAttribute(
      "placeholder",
      "美股代碼 (e.g. AAPL, BRK.B)",
    );
  });

  it("calls onChange with uppercased trimmed value on Enter", () => {
    const onChange = vi.fn();
    render(<StockSelector market="us" value="" onChange={onChange} />);
    const input = screen.getByTestId("stock-selector-input");
    fireEvent.change(input, { target: { value: "  aapl  " } });
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).toHaveBeenCalledWith("AAPL");
  });

  it("does not call onChange on Enter when input is empty", () => {
    const onChange = vi.fn();
    render(<StockSelector market="tw" value="" onChange={onChange} />);
    const input = screen.getByTestId("stock-selector-input");
    fireEvent.keyDown(input, { key: "Enter" });
    expect(onChange).not.toHaveBeenCalled();
  });

  it("has correct aria-label for TW market", () => {
    render(<StockSelector market="tw" value="" onChange={() => undefined} />);
    const input = screen.getByLabelText("台股代碼輸入");
    expect(input).toBeInTheDocument();
  });

  it("has correct aria-label for US market", () => {
    render(<StockSelector market="us" value="" onChange={() => undefined} />);
    const input = screen.getByLabelText("美股代碼輸入");
    expect(input).toBeInTheDocument();
  });
});
