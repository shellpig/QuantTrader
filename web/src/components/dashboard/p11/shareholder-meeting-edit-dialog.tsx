"use client";

import { useEffect, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { X } from "lucide-react";
import { apiDelete, apiPost } from "@/lib/api-client";
import type { P11EventCalendarEntry } from "@/types/analysis";

export function ShareholderMeetingEditDialog({
  open,
  onOpenChange,
  symbol,
  market,
  current,
  onSaved,
}: {
  open: boolean;
  onOpenChange: (next: boolean) => void;
  symbol: string;
  market: "tw" | "us";
  current: P11EventCalendarEntry | null;
  onSaved: () => Promise<void> | void;
}) {
  const [date, setDate] = useState("");
  const [meetingType, setMeetingType] = useState<"常會" | "臨時會">("常會");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open) return;
    setDate(current?.date ?? "");
    setMeetingType(current?.meeting_type === "臨時會" ? "臨時會" : "常會");
  }, [open, current]);

  const canSave = date.trim() !== "" && !loading;
  const canClear = current?.source === "manual" && !loading;

  async function handleSave() {
    if (!canSave) return;
    setLoading(true);
    try {
      await apiPost(
        `/api/analysis/p11/shareholder-meeting/override?market=${market}`,
        { symbol, date, meeting_type: meetingType },
      );
      await onSaved();
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  }

  async function handleClear() {
    if (!canClear) return;
    setLoading(true);
    try {
      await apiDelete(
        `/api/analysis/p11/shareholder-meeting/override?symbol=${encodeURIComponent(symbol)}&market=${market}`,
      );
      await onSaved();
      onOpenChange(false);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[92vw] max-w-md -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-950 p-4 text-slate-100">
          <div className="mb-3 flex items-center justify-between">
            <Dialog.Title className="text-base font-semibold">編輯股東會日期</Dialog.Title>
            <Dialog.Close asChild>
              <button type="button" className="rounded-md border border-slate-700 p-1 hover:bg-slate-800" aria-label="close">
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <div className="space-y-3 text-sm">
            <div>
              <p className="mb-1 text-slate-400">目前來源</p>
              <p className="text-slate-200" data-testid="p11-shareholder-current-source">
                {current?.source ?? "無"}
              </p>
            </div>

            <label className="block">
              <span className="mb-1 block text-slate-400">日期</span>
              <input
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
                className="w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1.5 text-slate-100"
              />
            </label>

            <fieldset>
              <legend className="mb-1 text-slate-400">會議類型</legend>
              <div className="flex items-center gap-4">
                <label className="inline-flex items-center gap-1.5">
                  <input
                    type="radio"
                    name="meeting_type"
                    value="常會"
                    checked={meetingType === "常會"}
                    onChange={() => setMeetingType("常會")}
                  />
                  常會
                </label>
                <label className="inline-flex items-center gap-1.5">
                  <input
                    type="radio"
                    name="meeting_type"
                    value="臨時會"
                    checked={meetingType === "臨時會"}
                    onChange={() => setMeetingType("臨時會")}
                  />
                  臨時會
                </label>
              </div>
            </fieldset>
          </div>

          <div className="mt-4 flex items-center justify-end gap-2">
            {canClear ? (
              <button
                type="button"
                className="rounded-md border border-amber-700 px-3 py-1.5 text-xs text-amber-200 hover:bg-amber-900/30"
                onClick={handleClear}
                disabled={loading}
              >
                清除手動
              </button>
            ) : null}
            <button
              type="button"
              className="rounded-md border border-slate-700 px-3 py-1.5 text-xs text-slate-200 hover:bg-slate-800 disabled:opacity-50"
              onClick={handleSave}
              disabled={!canSave}
            >
              儲存
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
