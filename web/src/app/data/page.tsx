// Data management page — shell (Phase 10-B, to be implemented in 10-C)

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "資料管理 | QuantTrader",
  description: "管理本機歷史資料、更新與重建。",
};

export default function DataPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-bold text-foreground">資料管理</h1>
      <p className="text-muted-foreground">
        此頁面將在 Phase 10-C 實作完整內容。
      </p>
    </div>
  );
}
