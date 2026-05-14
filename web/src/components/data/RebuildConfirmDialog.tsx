"use client";

// Two-step confirmation for "全部重建" — destructive batch operation (Phase 10-C-2)

import * as Dialog from "@radix-ui/react-dialog";
import { AlertTriangle, Hammer, X } from "lucide-react";
import type { Market } from "@/types/market";

interface RebuildConfirmDialogProps {
  open: boolean;
  market: Market;
  symbolCount: number;
  onClose: () => void;
  onConfirm: () => void;
  isRebuilding?: boolean;
}

export function RebuildConfirmDialog({
  open,
  market,
  symbolCount,
  onClose,
  onConfirm,
  isRebuilding = false,
}: RebuildConfirmDialogProps) {
  const marketLabel = market === "us" ? "美股" : "台股";

  return (
    <Dialog.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-slate-950/70 backdrop-blur-sm" />
        <Dialog.Content
          data-testid="rebuild-dialog"
          className="fixed left-1/2 top-1/2 z-50 w-[500px] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-slate-800 bg-slate-900 p-6 shadow-2xl"
        >
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-amber-500/15">
                <AlertTriangle className="h-5 w-5 text-amber-500" />
              </div>
              <div>
                <Dialog.Title className="text-base font-semibold text-slate-100">
                  確認重建全部 {marketLabel} 本機資料
                </Dialog.Title>
                <Dialog.Description className="mt-1.5 text-[13px] leading-relaxed text-slate-300">
                  此動作將清除 <span className="text-slate-100 font-medium">{symbolCount}</span>{" "}
                  個 {marketLabel} 標的的本機快取，再從資料來源重新下載。
                  過程可能耗時數分鐘；重建期間其他資料操作將被鎖定。
                  <br />
                  <span className="mt-2 block text-amber-400/80">
                    此操作無法中途取消且影響範圍大，請謹慎確認。
                  </span>
                </Dialog.Description>
              </div>
            </div>
            <Dialog.Close
              data-testid="rebuild-dialog-close"
              disabled={isRebuilding}
              className="-mr-1 -mt-1 rounded-md p-1 text-slate-500 hover:text-slate-300 disabled:opacity-40"
            >
              <X className="h-4 w-4" />
            </Dialog.Close>
          </div>

          <div className="mt-6 flex items-center justify-end gap-2 border-t border-slate-800 pt-4">
            <button
              data-testid="rebuild-dialog-cancel"
              onClick={onClose}
              disabled={isRebuilding}
              className="h-9 rounded-md border border-slate-700/80 bg-slate-900/40 px-4 text-sm text-slate-200 hover:bg-slate-800/60 disabled:opacity-50"
            >
              取消
            </button>
            <button
              data-testid="rebuild-dialog-confirm"
              onClick={onConfirm}
              disabled={isRebuilding}
              className="inline-flex h-9 items-center gap-1.5 rounded-md bg-amber-600 px-4 text-sm font-medium text-white hover:bg-amber-500 disabled:bg-amber-900/40 disabled:text-amber-300/40"
            >
              <Hammer className="h-3.5 w-3.5" />
              {isRebuilding ? "重建中…" : "確認重建"}
            </button>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
