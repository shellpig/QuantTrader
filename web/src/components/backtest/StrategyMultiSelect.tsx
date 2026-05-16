"use client";

interface StrategyPreset {
  name: string;
  type: string;
  params: Record<string, unknown>;
}

interface StrategyMultiSelectProps {
  presets: StrategyPreset[];
  selectedIndices: number[];
  onChange: (indices: number[]) => void;
  disabled?: boolean;
}

export function StrategyMultiSelect({
  presets,
  selectedIndices,
  onChange,
  disabled = false,
}: StrategyMultiSelectProps) {
  const selected = new Set(selectedIndices);
  const allChecked = presets.length > 0 && selectedIndices.length === presets.length;

  function toggleOne(index: number) {
    if (disabled) return;
    if (selected.has(index)) {
      onChange(selectedIndices.filter((i) => i !== index));
      return;
    }
    onChange([...selectedIndices, index].sort((a, b) => a - b));
  }

  function toggleAll(next: boolean) {
    if (disabled) return;
    if (next) {
      onChange(presets.map((_, i) => i));
      return;
    }
    onChange([]);
  }

  return (
    <div data-testid="strategy-multi-select" className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <label className="text-xs text-slate-400">策略（可複選）</label>
        <label className="inline-flex items-center gap-1 text-xs text-slate-400">
          <input
            type="checkbox"
            data-testid="strategy-select-all"
            checked={allChecked}
            disabled={disabled || presets.length === 0}
            onChange={(e) => toggleAll(e.target.checked)}
          />
          全選
        </label>
      </div>

      <div className="grid gap-1 rounded border border-slate-700 bg-slate-800/40 p-2">
        {presets.map((preset, index) => (
          <label
            key={`${preset.name}-${index}`}
            className={`inline-flex items-center gap-2 text-sm ${
              disabled ? "opacity-60" : "text-slate-200"
            }`}
          >
            <input
              type="checkbox"
              data-testid={`strategy-option-${index}`}
              checked={selected.has(index)}
              disabled={disabled}
              onChange={() => toggleOne(index)}
            />
            <span>{preset.name}</span>
          </label>
        ))}
      </div>
    </div>
  );
}

