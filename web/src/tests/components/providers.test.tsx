import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Providers } from "@/components/providers";

const mockToaster = vi.fn();

vi.mock("sonner", () => ({
  Toaster: (props: unknown) => {
    mockToaster(props);
    return <div data-testid="sonner-toaster" />;
  },
}));

vi.mock("@/components/command-palette", () => ({
  CommandPalette: () => <div data-testid="command-palette" />,
}));

describe("Providers", () => {
  it("renders children, Toaster and CommandPalette with expected props", () => {
    render(
      <Providers>
        <div data-testid="child">content</div>
      </Providers>,
    );

    expect(screen.getByTestId("child")).toBeInTheDocument();
    expect(screen.getByTestId("sonner-toaster")).toBeInTheDocument();
    expect(screen.getByTestId("command-palette")).toBeInTheDocument();

    expect(mockToaster).toHaveBeenCalledWith(
      expect.objectContaining({
        position: "bottom-right",
        duration: 3000,
        richColors: true,
        closeButton: true,
      }),
    );
  });
});
