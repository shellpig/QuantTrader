// Dashboard page — shell (Phase 10-B, to be implemented in 10-D)

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "個股分析 | QuantTrader",
  description: "股票技術分析、籌碼分析與 AI 劇本。",
};

export default function DashboardPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">個股分析</h1>
      <p className="text-muted-foreground">
        此頁面將在 Phase 10-D 實作完整內容。
      </p>
    </div>
  );
}
