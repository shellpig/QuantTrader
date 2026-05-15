import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { CommandPalette } from "@/components/command-palette";

const mockPush = vi.fn();
const mockApiFetch = vi.fn();
const mockEntryAction = vi.fn();
const mockRouter = { push: mockPush };
const mockEntries = [
  {
    id: "nav-data",
    label: "資料管理",
    group: "pages" as const,
    action: mockEntryAction,
  },
];

vi.mock("next/navigation", () => ({
  useRouter: () => mockRouter,
}));

vi.mock("@/lib/api-client", () => ({
  apiFetch: (...args: unknown[]) => mockApiFetch(...args),
}));

vi.mock("@/hooks/use-command-palette", () => ({
  useCommandEntries: () => mockEntries,
  useCommandPaletteStockMarket: () => "tw",
}));

vi.mock("cmdk", () => {
  const Dialog = ({
    open,
    children,
  }: {
    open: boolean;
    children: React.ReactNode;
  }) => (open ? <div data-testid="cmdk-dialog">{children}</div> : null);

  const Input = ({
    value,
    onValueChange,
    placeholder,
    autoFocus,
  }: {
    value: string;
    onValueChange: (next: string) => void;
    placeholder?: string;
    autoFocus?: boolean;
  }) => (
    <input
      data-testid="cmdk-input"
      value={value}
      onChange={(event) => onValueChange(event.target.value)}
      placeholder={placeholder}
      autoFocus={autoFocus}
    />
  );

  const List = ({ children }: { children: React.ReactNode }) => <div>{children}</div>;
  const Group = ({
    heading,
    children,
  }: {
    heading?: string;
    children: React.ReactNode;
  }) => (
    <section>
      {heading ? <h3>{heading}</h3> : null}
      {children}
    </section>
  );
  const Item = ({
    children,
    onSelect,
  }: {
    children: React.ReactNode;
    onSelect?: () => void;
  }) => (
    <button type="button" onClick={() => onSelect?.()}>
      {children}
    </button>
  );
  const Empty = ({ children }: { children: React.ReactNode }) => (
    <div>{children}</div>
  );

  return {
    Command: {
      Dialog,
      Input,
      List,
      Group,
      Item,
      Empty,
    },
  };
});

describe("CommandPalette", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("opens with Ctrl+K and closes with Esc", () => {
    render(<CommandPalette />);
    expect(screen.queryByTestId("cmdk-dialog")).not.toBeInTheDocument();
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    expect(screen.getByTestId("cmdk-dialog")).toBeInTheDocument();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(screen.queryByTestId("cmdk-dialog")).not.toBeInTheDocument();
  });

  it("opens with slash and focuses input", () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "/" });
    const input = screen.getByTestId("cmdk-input");
    expect(input).toBeInTheDocument();
    expect(document.activeElement).toBe(input);
  });

  it("does not open on slash inside input", () => {
    render(
      <div>
        <input data-testid="external-input" />
        <CommandPalette />
      </div>,
    );
    const externalInput = screen.getByTestId("external-input");
    externalInput.focus();
    fireEvent.keyDown(externalInput, { key: "/" });
    expect(screen.queryByTestId("cmdk-dialog")).not.toBeInTheDocument();
  });

  it("runs page entry action and closes", async () => {
    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    await userEvent.click(screen.getByRole("button", { name: "資料管理" }));
    expect(mockEntryAction).toHaveBeenCalled();
    expect(screen.queryByTestId("cmdk-dialog")).not.toBeInTheDocument();
  });

  it("shows stock search results and navigates to dashboard", async () => {
    mockApiFetch.mockResolvedValueOnce({
      data: [{ symbol: "2330", name: "台積電" }],
      meta: { market: "tw", count: 1 },
    });

    render(<CommandPalette />);
    fireEvent.keyDown(window, { key: "k", ctrlKey: true });
    fireEvent.change(screen.getByTestId("cmdk-input"), {
      target: { value: "2330" },
    });

    await waitFor(() => {
      expect(mockApiFetch).toHaveBeenCalled();
      expect(screen.getByRole("button", { name: "2330 台積電" })).toBeInTheDocument();
    });

    await userEvent.click(screen.getByRole("button", { name: "2330 台積電" }));
    expect(mockPush).toHaveBeenCalledWith("/dashboard?symbol=2330");
  });
});
