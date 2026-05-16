"use client";

import { SecretsSection } from "./secrets-section";
import { StrategyPresetsSection } from "./strategy-presets-section";
import { ThemeSection } from "./theme-section";
import { AiToggleSection } from "./ai-toggle-section";

export function SettingsPageClient() {
  return (
    <div className="space-y-8">
      <h1 className="text-2xl font-bold text-foreground">設定</h1>
      <SecretsSection />
      <hr className="border-slate-800" />
      <StrategyPresetsSection />
      <hr className="border-slate-800" />
      <ThemeSection />
      <hr className="border-slate-800" />
      <AiToggleSection />
    </div>
  );
}
