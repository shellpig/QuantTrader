// Job progress bar — shows current/total + active symbol (Phase 10-C-2)

interface ProgressBarProps {
  current: number;
  total: number;
  currentSymbol?: string;
  className?: string;
}

export function ProgressBar({ current, total, currentSymbol, className }: ProgressBarProps) {
  const pct = total > 0 ? Math.min((current / total) * 100, 100) : 0;

  return (
    <div data-testid="progress-bar" className={`flex flex-col gap-1.5 ${className ?? ""}`}>
      <div className="flex items-center justify-between text-[12px] text-slate-400">
        <span>
          {currentSymbol ? (
            <>
              處理 <span className="font-mono text-slate-200">{currentSymbol}</span>…
            </>
          ) : (
            "準備中…"
          )}
        </span>
        <span data-testid="progress-count">
          {current} / {total}
        </span>
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-800">
        <div
          data-testid="progress-fill"
          className="h-full rounded-full bg-sky-500 transition-all duration-300"
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}
