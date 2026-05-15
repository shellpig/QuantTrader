// Tests for ChatPageClient component (Phase 10-F-1)
// Uses fake timers to advance the mock streaming setInterval.

import { render, screen, fireEvent, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { ChatPageClient } from "@/components/ai/chat-page-client";

// scrollIntoView is not implemented in jsdom
window.HTMLElement.prototype.scrollIntoView = vi.fn();

// Pre-accept disclaimer so tests start at the chat view
beforeEach(() => {
  localStorage.setItem("ai_chat.disclaimer_accepted_v1", "1");
  vi.useFakeTimers();
});

afterEach(() => {
  localStorage.clear();
  vi.useRealTimers();
});

describe("ChatPageClient", () => {
  it("renders chat page container", () => {
    render(<ChatPageClient />);
    // After useEffect resolves accepted state
    act(() => { vi.runAllTimers(); });
    expect(screen.getByTestId("chat-page")).toBeInTheDocument();
  });

  it("shows greeting message on load", async () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });
    expect(screen.getByText(/可提問範例/)).toBeInTheDocument();
  });

  it("user bubble appears immediately after send", () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });

    const input = screen.getByTestId("chat-input-field");
    fireEvent.change(input, { target: { value: "2330 的 RSI？" } });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    expect(screen.getByText("2330 的 RSI？")).toBeInTheDocument();
  });

  it("input clears after send", () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });

    const input = screen.getByTestId("chat-input-field") as HTMLInputElement;
    fireEvent.change(input, { target: { value: "測試問題" } });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    expect(input.value).toBe("");
  });

  it("assistant bubble grows character by character (fake timer)", () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });

    const input = screen.getByTestId("chat-input-field");
    fireEvent.change(input, { target: { value: "hi" } });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    // Advance 50ms (2 chars at 25ms each)
    act(() => { vi.advanceTimersByTime(50); });
    const assistantBubbles = screen.getAllByTestId("message-bubble-assistant");
    const last = assistantBubbles[assistantBubbles.length - 1];
    // Content should have started streaming (non-empty)
    expect(last.textContent).toBeTruthy();

    // Advance all remaining timers to finish stream
    act(() => { vi.runAllTimers(); });
    expect(last.textContent).toMatch(/AI 串接尚未開放/);
  });

  it("empty or whitespace-only input does not send", () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });

    const initialBubbleCount = screen.getAllByTestId(/message-bubble/).length;
    const input = screen.getByTestId("chat-input-field");
    fireEvent.change(input, { target: { value: "   " } });
    fireEvent.click(screen.getByTestId("chat-send-button"));

    expect(screen.getAllByTestId(/message-bubble/).length).toBe(initialBubbleCount);
  });

  it("Enter key triggers send", () => {
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });

    const input = screen.getByTestId("chat-input-field");
    fireEvent.change(input, { target: { value: "Enter 送出" } });
    fireEvent.keyDown(input, { key: "Enter" });

    expect(screen.getByText("Enter 送出")).toBeInTheDocument();
  });

  it("shows disclaimer gate when localStorage key absent", () => {
    localStorage.clear();
    render(<ChatPageClient />);
    act(() => { vi.runAllTimers(); });
    expect(screen.getByTestId("disclaimer-gate")).toBeInTheDocument();
  });
});
