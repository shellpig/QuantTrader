import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { DefaultErrorFallback, ErrorBoundary } from "@/components/error-boundary";

const mockRefresh = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ refresh: mockRefresh }),
}));

function Crash({ message = "boom" }: { message?: string }) {
  throw new Error(message);
  return null;
}

describe("ErrorBoundary", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
  });

  it("renders default fallback when child throws", () => {
    render(
      <ErrorBoundary>
        <Crash />
      </ErrorBoundary>,
    );
    expect(screen.getByTestId("error-boundary-fallback")).toBeInTheDocument();
    expect(screen.getByText("執行發生錯誤")).toBeInTheDocument();
  });

  it("resets and refreshes router when clicking 重置", async () => {
    const reset = vi.fn();
    render(
      <DefaultErrorFallback error={new Error("temporary")} reset={reset} />,
    );
    await userEvent.click(screen.getByRole("button", { name: "重置" }));
    expect(reset).toHaveBeenCalled();
    expect(mockRefresh).toHaveBeenCalled();
  });

  it("supports fallback function and fallback element", () => {
    const { unmount } = render(
      <ErrorBoundary fallback={<div>custom-node</div>}>
        <Crash />
      </ErrorBoundary>,
    );
    expect(screen.getByText("custom-node")).toBeInTheDocument();

    unmount();

    render(
      <ErrorBoundary fallback={(error) => <div>custom-fn:{error.message}</div>}>
        <Crash />
      </ErrorBoundary>,
    );
    expect(screen.getByText("custom-fn:boom")).toBeInTheDocument();
  });

  it("hides stack in production mode", () => {
    vi.stubEnv("NODE_ENV", "production");
    render(
      <ErrorBoundary>
        <Crash />
      </ErrorBoundary>,
    );
    expect(screen.queryByText(/Error: boom/)).not.toBeInTheDocument();
  });
});
