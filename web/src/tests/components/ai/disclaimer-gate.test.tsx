// Tests for DisclaimerGate component (Phase 10-F-1)

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { DisclaimerGate } from "@/components/ai/disclaimer-gate";

const STORAGE_KEY = "ai_chat.disclaimer_accepted_v1";

describe("DisclaimerGate", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("renders disclaimer card", () => {
    render(<DisclaimerGate onAccept={vi.fn()} />);
    expect(screen.getByTestId("disclaimer-gate")).toBeInTheDocument();
    expect(screen.getByText("免責聲明")).toBeInTheDocument();
  });

  it("shows 我了解 button", () => {
    render(<DisclaimerGate onAccept={vi.fn()} />);
    expect(screen.getByTestId("disclaimer-accept")).toBeInTheDocument();
    expect(screen.getByText("我了解")).toBeInTheDocument();
  });

  it("calls onAccept when button is clicked", () => {
    const onAccept = vi.fn();
    render(<DisclaimerGate onAccept={onAccept} />);
    fireEvent.click(screen.getByTestId("disclaimer-accept"));
    expect(onAccept).toHaveBeenCalledOnce();
  });

  it("writes localStorage key when button is clicked", () => {
    render(<DisclaimerGate onAccept={vi.fn()} />);
    expect(localStorage.getItem(STORAGE_KEY)).toBeNull();
    fireEvent.click(screen.getByTestId("disclaimer-accept"));
    expect(localStorage.getItem(STORAGE_KEY)).toBe("1");
  });

  it("renders disclaimer text in the card", () => {
    render(<DisclaimerGate onAccept={vi.fn()} />);
    expect(screen.getByText(/僅供研究參考/)).toBeInTheDocument();
  });
});
