// Settings page — shell (Phase 10-B, to be implemented in 10-G)

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "設定 | QuantTrader",
  description: "系統設定、API Key 管理與策略 preset。",
};

export default function SettingsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">設定</h1>
      <p className="text-muted-foreground">
        此頁面將在 Phase 10-G 實作完整內容。
      </p>
    </div>
  );
}
