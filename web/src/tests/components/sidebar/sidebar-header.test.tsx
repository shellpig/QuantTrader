import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("next/navigation", () => ({
  usePathname: () => "/dashboard",
  useRouter: () => ({ push: vi.fn() }),
}));

vi.mock("next/link", () => ({
  default: ({ href, children, ...rest }: React.AnchorHTMLAttributes<HTMLAnchorElement> & { href: string }) => (
    <a href={href} {...rest}>{children}</a>
  ),
}));

vi.mock("@/hooks/use-command-palette", () => ({
  useCommandPaletteEntry: () => undefined,
}));

import { Sidebar } from "@/components/sidebar";

describe("Sidebar header — Phase 11-E", () => {
  it("11-E-F1: displays FactorHammer as the app name", () => {
    render(<Sidebar />);
    expect(screen.getByTestId("sidebar-app-name")).toHaveTextContent("FactorHammer");
    expect(screen.queryByText("QuantTrader")).not.toBeInTheDocument();
  });

  it("11-E-F2: displays version from NEXT_PUBLIC_APP_VERSION with v prefix and muted class", () => {
    render(<Sidebar />);
    const versionEl = screen.getByTestId("sidebar-app-version");
    expect(versionEl).toBeInTheDocument();
    expect(versionEl.textContent).toMatch(/^v/);
    expect(versionEl).toHaveClass("text-muted-foreground");
    // version text should be visually smaller than the app name
    const nameEl = screen.getByTestId("sidebar-app-name");
    expect(nameEl).toHaveClass("text-base");
    expect(versionEl).toHaveClass("text-[10px]");
  });
});
