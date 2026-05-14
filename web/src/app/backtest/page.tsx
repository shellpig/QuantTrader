// Backtest page — shell (Phase 10-B, to be implemented in 10-E)

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "回測研究 | QuantTrader",
  description: "策略回測、參數掃描與 Walk-Forward 分析。",
};

export default function BacktestPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">回測研究</h1>
      <p className="text-muted-foreground">
        此頁面將在 Phase 10-E 實作完整內容。
      </p>
    </div>
  );
}
