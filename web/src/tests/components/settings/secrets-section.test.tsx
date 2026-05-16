// Tests for SecretsSection component (Phase 10-G-2)

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";

const mockToastSuccess = vi.fn();
const mockToastError = vi.fn();
vi.mock("@/hooks/use-toast", () => ({
  useToast: () => ({ success: mockToastSuccess, error: mockToastError, info: vi.fn(), dismiss: vi.fn() }),
}));

const mockMutate = vi.fn();
const mockUpdateSecrets = vi.fn();

vi.mock("@/hooks/use-config", () => ({
  useSecretsStatus: () => ({
    status: { openai: true, anthropic: false, gemini: false, finmind: false, google: false },
    isLoading: false,
    mutate: mockMutate,
  }),
  updateSecrets: (...args: unknown[]) => mockUpdateSecrets(...args),
}));

import { SecretsSection } from "@/components/settings/secrets-section";

describe("SecretsSection", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("renders all 5 provider inputs as password type", () => {
    render(<SecretsSection />);
    const inputs = screen.getAllByTestId(/^secret-input-/);
    expect(inputs).toHaveLength(5);
    for (const input of inputs) {
      expect(input).toHaveAttribute("type", "password");
    }
  });

  it("shows configured status for openai", () => {
    render(<SecretsSection />);
    expect(screen.getByText("✓")).toBeInTheDocument();
  });

  it("calls updateSecrets and shows success toast on save", async () => {
    mockUpdateSecrets.mockResolvedValueOnce(undefined);
    mockMutate.mockResolvedValueOnce(undefined);

    render(<SecretsSection />);

    fireEvent.change(screen.getByTestId("secret-input-anthropic"), {
      target: { value: "ant-new-key" },
    });
    fireEvent.click(screen.getByTestId("secrets-save-btn"));

    await waitFor(() => expect(mockUpdateSecrets).toHaveBeenCalledTimes(1));
    expect(mockUpdateSecrets).toHaveBeenCalledWith({ anthropic: "ant-new-key" });
    await waitFor(() => expect(mockToastSuccess).toHaveBeenCalledWith("API Key 已更新"));
  });

  it("shows error toast on API failure", async () => {
    mockUpdateSecrets.mockRejectedValueOnce(new Error("fail"));

    render(<SecretsSection />);

    fireEvent.change(screen.getByTestId("secret-input-openai"), {
      target: { value: "bad-key" },
    });
    fireEvent.click(screen.getByTestId("secrets-save-btn"));

    await waitFor(() => expect(mockToastError).toHaveBeenCalledTimes(1));
  });

  it("does not call updateSecrets when all inputs are empty", async () => {
    render(<SecretsSection />);
    fireEvent.click(screen.getByTestId("secrets-save-btn"));
    await waitFor(() => expect(mockUpdateSecrets).not.toHaveBeenCalled());
  });
});
