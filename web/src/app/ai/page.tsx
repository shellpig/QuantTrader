// AI Chat page — shell (Phase 10-B, to be implemented in 10-F)

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI 問答 | QuantTrader",
  description: "AI 股市問答助手。",
};

export default function AiPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">AI 問答</h1>
      <p className="text-muted-foreground">
        此頁面將在 Phase 10-F 實作完整內容。
      </p>
    </div>
  );
}
