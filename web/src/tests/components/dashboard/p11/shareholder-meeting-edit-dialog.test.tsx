import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { ShareholderMeetingEditDialog } from "@/components/dashboard/p11/shareholder-meeting-edit-dialog";

const apiPostMock = vi.fn();
const apiDeleteMock = vi.fn();

vi.mock("@/lib/api-client", () => ({
  apiPost: (...args: unknown[]) => apiPostMock(...args),
  apiDelete: (...args: unknown[]) => apiDeleteMock(...args),
}));

describe("ShareholderMeetingEditDialog", () => {
  it("disables save when date is empty and allows meeting-type switch", () => {
    render(
      <ShareholderMeetingEditDialog
        open
        onOpenChange={() => undefined}
        symbol="2330"
        market="tw"
        current={null}
        onSaved={() => undefined}
      />,
    );

    expect(screen.getByRole("button", { name: "儲存" })).toBeDisabled();
    const temporary = screen.getByRole("radio", { name: "臨時會" });
    fireEvent.click(temporary);
    expect(temporary).toBeChecked();
  });

  it("calls POST and mutate callback on save", async () => {
    const onSaved = vi.fn();
    apiPostMock.mockResolvedValue({ data: {}, meta: {} });

    render(
      <ShareholderMeetingEditDialog
        open
        onOpenChange={() => undefined}
        symbol="2330"
        market="tw"
        current={{ date: "2026-06-30", meeting_type: "常會", source: "auto", is_manual: false }}
        onSaved={onSaved}
      />,
    );

    fireEvent.change(screen.getByLabelText("日期"), { target: { value: "2026-07-01" } });
    fireEvent.click(screen.getByRole("button", { name: "儲存" }));

    await waitFor(() => {
      expect(apiPostMock).toHaveBeenCalledTimes(1);
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
  });

  it("shows clear button for manual source and calls DELETE", async () => {
    const onSaved = vi.fn();
    apiDeleteMock.mockResolvedValue({ data: {}, meta: {} });

    render(
      <ShareholderMeetingEditDialog
        open
        onOpenChange={() => undefined}
        symbol="2330"
        market="tw"
        current={{ date: "2026-06-30", meeting_type: "常會", source: "manual", is_manual: true }}
        onSaved={onSaved}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "清除手動" }));
    await waitFor(() => {
      expect(apiDeleteMock).toHaveBeenCalledTimes(1);
      expect(onSaved).toHaveBeenCalledTimes(1);
    });
  });
});
