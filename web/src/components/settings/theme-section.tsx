"use client";

import { useTheme } from "@/components/theme-provider";

export function ThemeSection() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";

  return (
    <section aria-labelledby="theme-heading">
      <h2
        id="theme-heading"
        className="mb-4 text-lg font-semibold text-foreground"
      >
        外觀主題
      </h2>
      <div className="flex items-center gap-3">
        <span className="text-sm text-muted-foreground">主題</span>
        <button
          data-testid="theme-toggle"
          role="switch"
          aria-checked={isDark}
          aria-label="切換深色 / 淺色主題"
          onClick={() => setTheme(isDark ? "light" : "dark")}
          className="relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          style={{ backgroundColor: isDark ? "#1d4ed8" : "#94a3b8" }}
        >
          <span
            className="inline-block h-4 w-4 rounded-full bg-white shadow transition-transform"
            style={{
              transform: isDark ? "translateX(1.375rem)" : "translateX(0.125rem)",
            }}
          />
        </button>
        <span className="text-sm text-foreground">
          {isDark ? "深色" : "淺色"}
        </span>
      </div>
    </section>
  );
}
