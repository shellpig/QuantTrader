"use client";

import { useState } from "react";
import { Trash2, Plus, RotateCcw } from "lucide-react";
import {
  useStrategyPresets,
  upsertStrategyPreset,
  deleteStrategyPreset,
  restoreStrategyDefaults,
} from "@/hooks/use-config";
import type { StrategyPreset } from "@/hooks/use-config";
import { useToast } from "@/hooks/use-toast";
import { StrategyPresetDialog } from "./strategy-preset-dialog";

export function StrategyPresetsSection() {
  const { presets, isLoading, mutate } = useStrategyPresets();
  const toast = useToast();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editPreset, setEditPreset] = useState<StrategyPreset | null>(null);

  async function handleSave(preset: StrategyPreset, isNew: boolean) {
    try {
      await upsertStrategyPreset(preset);
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
              className="flex items-center justify-between rounded border border-slate-800 bg-slate-900 px-4 py-3"
            >
              <div>
                <span className="text-sm font-medium text-slate-100">
                  {p.name}
                </span>
                <span className="ml-2 text-xs text-slate-500">{p.type}</span>
              </div>
              <button
                data-testid={`delete-preset-${p.name}`}
                onClick={() => handleDelete(p.name)}
                className="rounded p-1 text-slate-500 hover:text-rose-400"
                aria-label={`刪除 ${p.name}`}
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
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
