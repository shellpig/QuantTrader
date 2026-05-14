"use client";

// Add symbol dialog — uses StockSelector (Phase 10-C-2)
// On submit: triggers a data_update job for the entered symbol.

import { useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Plus, X } from "lucide-react";
import { StockSelector } from "@/components/stock-selector";
import type { Market } from "@/types/market";

interface AddSymbolDialogProps {
  open: boolean;
  market: Market;
  onClose: () => void;
  onSubmit: (symbol: string) => Promise<void>;
}

export function AddSymbolDialog({ open, market, onClose, onSubmit }: AddSymbolDialogProps) {
  const [symbol, setSymbol] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function handleSubmit() {
    const trimmed = symbol.trim();
    if (!trimmed || isSubmitting) return;
    setIsSubmitting(true);
    try {
      await onSubmit(trimmed);
      setSymbol("");
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  }

  function handleClose() {
    if (isSubmitting) return;
    setSymbol("");
    onClose();
  }

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && handleClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm" />
        <Dialog.Content
          data-testid="add-dialog"
          className="fixed left-1/2 top-1/2 z-50 w-[440px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-sky-500/15">
                <Plus className="h-4 w-4 text-sky-400" />
              </div>
              <Dialog.Title className="text-base font-semibold text-slate-100">
                新增標的
              </Dialog.Title>
            </div>
            <Dialog.Close
              data-testid="add-dialog-close"
              disabled={isSubmitting}
              className="-mr-1 -mt-1 rounded-md p-1 text-slate-500 hover:text-slate-300 disabled:opacity-40"
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <Dialog.Description className="mt-2 text-[13px] text-slate-400">
            {market === "tw"
              ? "輸入台股代碼或名稱，系統將從 FinMind 下載歷史日 K 資料。"
              : "輸入美股代碼（如 AAPL、BRK.B），系統將從 yfinance 下載日 K 資料。"}
          </Dialog.Description>

          <div className="mt-4">
            <StockSelector
              market={market}
              value={symbol}
              onChange={setSymbol}
              onSearch={handleSubmit}
              placeholder={
                market === "tw"
                  ? "代碼或名稱（如 2330 / 台積電）"
                  : "代碼（如 AAPL、BRK.B）"
              }
            />
            <p className="mt-1.5 text-[11.5px] text-slate-500">
              輸入後按 Enter 或點擊確認新增
            </p>
          </div>

          <div className="mt-5 flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
            <button
              data-testid="add-dialog-cancel"
              onClick={handleClose}
              disabled={isSubmitting}
              className="h-9 rounded-md border border-slate-700/80 bg-slate-900/40 px-4 text-sm text-slate-200 hover:bg-slate-800/60 disabled:opacity-50"
            >
              取消
            </button>
            <button
              data-testid="add-dialog-confirm"
              onClick={handleSubmit}
              disabled={!symbol.trim() || isSubmitting}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-sky-600 px-4 text-sm font-medium text-white hover:bg-sky-500 disabled:bg-sky-900/40 disabled:text-sky-300/40"
            >
              <Plus className="h-3.5 w-3.5" />
              {isSubmitting ? "新增中…" : "確認新增"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
