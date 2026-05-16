import { test, expect } from "@playwright/test";

const PAGES = [
  { name: "個股分析", href: "/dashboard",  desktopTestId: "sidebar-nav-dashboard", mobileTestId: "mobile-nav-dashboard" },
  { name: "回測研究", href: "/backtest",   desktopTestId: "sidebar-nav-backtest",  mobileTestId: "mobile-nav-backtest" },
  { name: "資料管理", href: "/data",       desktopTestId: "sidebar-nav-data",      mobileTestId: "mobile-nav-data" },
  { name: "AI 問答",  href: "/ai",         desktopTestId: "sidebar-nav-ai",        mobileTestId: "mobile-nav-ai" },
  { name: "設定",     href: "/settings",   desktopTestId: "sidebar-nav-settings",  mobileTestId: "mobile-nav-settings" },
];

test.describe("Navigation — desktop sidebar", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  for (const page of PAGES) {
    test(`can reach ${page.name} via sidebar`, async ({ page: pw }) => {
      await pw.addInitScript(() => {
        const style = document.createElement("style");
        style.textContent = "nextjs-portal { pointer-events: none !important; display: none !important; }";
        document.documentElement.appendChild(style);
      });
      // Go from a non-target page to avoid clicking active link
      const startFrom = page.href === "/settings" ? "/data" : "/settings";
      await pw.goto(startFrom);
      const link = pw.getByTestId(page.desktopTestId).first();
      await link.click();
      await expect(pw).toHaveURL(page.href);
    });
  }

  test("Command Palette opens and navigates to Settings", async ({ page: pw }) => {
    await pw.goto("/dashboard");
    // Open command palette with Ctrl+K
    await pw.keyboard.press("Control+k");
    // Wait for the command palette input (more reliable than dialog role check)
    const input = pw.locator('input[placeholder="輸入頁面名稱或股票代碼..."]');
    await expect(input).toBeVisible({ timeout: 8000 });
    // Type to filter for 設定 page
    await input.fill("設定");
    // Wait for the item and click it
    const settingsItem = pw.locator('[cmdk-item]', { hasText: "設定" }).first();
    await expect(settingsItem).toBeVisible({ timeout: 5000 });
    await settingsItem.click();
    await expect(pw).toHaveURL("/settings");
  });
});

test.describe("Navigation — mobile bottom tab bar", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  for (const page of PAGES) {
    test(`can reach ${page.name} via bottom tab bar`, async ({ page: pw }) => {
      // Inject CSS before every navigation to disable Next.js dev portal overlay
      await pw.addInitScript(() => {
        const style = document.createElement("style");
        style.textContent = "nextjs-portal { pointer-events: none !important; display: none !important; }";
        document.documentElement.appendChild(style);
      });
      // Start from a page that is NOT the target to avoid clicking an already-active link
      const startFrom = page.href === "/settings" ? "/data" : "/settings";
      await pw.goto(startFrom);
      const link = pw.getByTestId(page.mobileTestId).first();
      await expect(link).toBeVisible();
      await pw.evaluate((testid) => {
        const el = document.querySelector(`[data-testid="${testid}"]`) as HTMLElement;
        el?.click();
      }, page.mobileTestId);
      await expect(pw).toHaveURL(page.href);
    });
  }

  test("bottom tab bar is visible on mobile", async ({ page: pw }) => {
    await pw.goto("/dashboard");
    const tabBar = pw.locator('nav[aria-label="手機底部導覽"]');
    await expect(tabBar).toBeVisible();
  });

  test("active tab has correct aria-current", async ({ page: pw }) => {
    await pw.goto("/backtest");
    const activeTab = pw.getByTestId("mobile-nav-backtest").first();
    await expect(activeTab).toHaveAttribute("aria-current", "page");
  });
});
