"use client";

import { useState } from "react";
import { Trash2, Plus, RotateCcw, Pencil } from "lucide-react";
import {
  useStrategyPresets,
  upsertStrategyPreset,
  deleteStrategyPreset,
  restoreStrategyDefaults,
} from "@/hooks/use-config";
import type { StrategyPreset } from "@/hooks/use-config";
import { useToast } from "@/hooks/use-toast";
import { StrategyPresetDialog } from "./strategy-preset-dialog";

function formatParamsSummary(params: Record<string, number>): string {
  return Object.entries(params)
    .map(([key, value]) => `${key}=${value}`)
    .join(", ");
}

function formatMarketLabel(market: StrategyPreset["market"]): string {
  if (market === "tw") return "TW";
  if (market === "us") return "US";
  return "未指定";
}

export function StrategyPresetsSection() {
  const { presets, isLoading, mutate } = useStrategyPresets();
  const toast = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editPreset, setEditPreset] = useState<StrategyPreset | null>(null);

  async function handleSave(preset: StrategyPreset, isNew: boolean) {
    const originalName = !isNew ? editPreset?.name.trim() : "";
    const newName = preset.name.trim();
    try {
      await upsertStrategyPreset(preset);
      if (originalName && originalName !== newName) {
        await deleteStrategyPreset(originalName);
      }
      await mutate();
      toast.success(
        isNew ? `已新增策略：${preset.name}` : `已更新策略：${preset.name}`,
      );
    } catch {
      toast.error("儲存策略失敗");
    }
    setDialogOpen(false);
    setEditPreset(null);
  }

  async function handleDelete(name: string) {
    try {
      await deleteStrategyPreset(name);
      await mutate();
      toast.success(`已刪除策略：${name}`);
    } catch {
      toast.error("刪除策略失敗");
    }
  }

  async function handleRestore() {
    try {
      const count = await restoreStrategyDefaults();
      await mutate();
      toast.success(`已重置為預設 ${count} 組策略`);
    } catch {
      toast.error("重置失敗");
    }
  }

  return (
    <section aria-labelledby="presets-heading">
      <div className="mb-4 flex items-center justify-between">
        <h2
          id="presets-heading"
          className="text-lg font-semibold text-foreground"
        >
          策略 Preset
        </h2>
        <div className="flex gap-2">
          <button
            data-testid="restore-defaults-btn"
            onClick={handleRestore}
            className="flex items-center gap-1.5 rounded border border-slate-700 px-3 py-1.5 text-sm text-slate-300 hover:bg-slate-800"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            重置預設
          </button>
          <button
            data-testid="add-preset-btn"
            onClick={() => {
              setEditPreset(null);
              setDialogOpen(true);
            }}
            className="flex items-center gap-1.5 rounded bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-500"
          >
            <Plus className="h-3.5 w-3.5" />
            新增
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="text-sm text-muted-foreground">載入中…</div>
      ) : presets.length === 0 ? (
        <div className="text-sm text-muted-foreground">尚無策略 preset</div>
      ) : (
        <div className="space-y-2">
          {presets.map((p) => (
            <div
              key={p.name}
              data-testid={`preset-row-${p.name}`}
              onClick={() => {
                setEditPreset(p);
                setDialogOpen(true);
              }}
              className="flex cursor-pointer items-center justify-between rounded border border-slate-800 bg-slate-900 px-4 py-3 hover:border-slate-700"
            >
              <div>
                <span className="text-sm font-medium text-slate-100">
                  {p.name}
                </span>
                <span className="ml-2 text-xs text-slate-500">{p.type}</span>
                <span
                  data-testid={`preset-market-${p.name}`}
                  className="ml-2 rounded border border-slate-700 px-1.5 py-0.5 text-[10px] text-slate-300"
                >
                  {formatMarketLabel(p.market)}
                </span>
                <p
                  data-testid={`preset-summary-${p.name}`}
                  className="mt-1 text-xs text-slate-400"
                >
                  {formatParamsSummary(p.params)}
                </p>
              </div>
              <div className="flex items-center gap-1">
                <button
                  data-testid={`edit-preset-${p.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    setEditPreset(p);
                    setDialogOpen(true);
                  }}
                  className="rounded p-1 text-slate-500 hover:text-sky-400"
                  aria-label={`編輯 ${p.name}`}
                >
                  <Pencil className="h-3.5 w-3.5" />
                </button>
                <button
                  data-testid={`delete-preset-${p.name}`}
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(p.name);
                  }}
                  className="rounded p-1 text-slate-500 hover:text-rose-400"
                  aria-label={`刪除 ${p.name}`}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      <StrategyPresetDialog
        open={dialogOpen}
        initialPreset={editPreset}
        onClose={() => {
          setDialogOpen(false);
          setEditPreset(null);
        }}
        onSave={handleSave}
      />
    </section>
  );
}
