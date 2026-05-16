"use client";

import * as Tooltip from "@radix-ui/react-tooltip";

export function AiToggleSection() {
  return (
    <section aria-labelledby="ai-toggle-heading">
      <h2
        id="ai-toggle-heading"
        className="mb-4 text-lg font-semibold text-foreground"
      >
        AI 分析
      </h2>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">AI 分析功能</span>
        <Tooltip.Provider delayDuration={200}>
          <Tooltip.Root>
            <Tooltip.Trigger asChild>
              <button
                data-testid="ai-toggle"
                role="switch"
                aria-checked={false}
                disabled
                aria-label="AI 分析（已停用）"
                className="relative inline-flex h-6 w-11 cursor-not-allowed items-center rounded-full bg-slate-700 opacity-50"
              >
                <span
                  className="inline-block h-4 w-4 rounded-full bg-white shadow"
                  style={{ transform: "translateX(0.125rem)" }}
                />
              </button>
            </Tooltip.Trigger>
            <Tooltip.Portal>
              <Tooltip.Content
                data-testid="ai-tooltip"
                className="rounded bg-slate-800 px-3 py-2 text-xs text-slate-200 shadow-md"
                sideOffset={5}
              >
                AI 功能在個人版中永久停用
                <Tooltip.Arrow className="fill-slate-800" />
              </Tooltip.Content>
            </Tooltip.Portal>
          </Tooltip.Root>
        </Tooltip.Provider>
        <span className="text-sm text-slate-500">（永久停用）</span>
      </div>
    </section>
  );
}
