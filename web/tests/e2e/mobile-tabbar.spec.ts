import { test, expect } from "@playwright/test";

/**
 * E2E smoke: mobile bottom tab bar
 * Only runs on mobile-chromium project (375×667).
 */
test.describe("Mobile Tab Bar", () => {
  test.use({ viewport: { width: 375, height: 667 } });

  const TAB_ITEMS = [
    { testid: "mobile-nav-dashboard", href: "/dashboard" },
    { testid: "mobile-nav-backtest",  href: "/backtest" },
    { testid: "mobile-nav-data",      href: "/data" },
    { testid: "mobile-nav-ai",        href: "/ai" },
    { testid: "mobile-nav-settings",  href: "/settings" },
  ];

  test("bottom tab bar is visible on mobile viewport", async ({ page }) => {
    await page.goto("/dashboard");
    const tabBar = page.locator('nav[aria-label="手機底部導覽"]');
    await expect(tabBar).toBeVisible();
  });

  test("desktop sidebar is NOT visible on mobile viewport", async ({ page }) => {
    await page.goto("/dashboard");
    const sidebar = page.locator("aside.lg\\:flex");
    // sidebar should be hidden (CSS hidden class — check it's not in viewport)
    await expect(sidebar).not.toBeInViewport();
  });

  for (const item of TAB_ITEMS) {
    test(`tapping ${item.testid} navigates to ${item.href}`, async ({ page }) => {
      // Start from a different page to avoid clicking an already-active tab
      const startFrom = item.href === "/settings" ? "/data" : "/settings";
      await page.goto(startFrom);
      const tab = page.getByTestId(item.testid).first();
      await expect(tab).toBeVisible();
      // Verify href is correct
      await expect(tab).toHaveAttribute("href", item.href);
      // Trigger navigation via JS click to bypass Next.js dev portal overlay
      await page.evaluate((testid) => {
        const el = document.querySelector(`[data-testid="${testid}"]`) as HTMLElement;
        el?.click();
      }, item.testid);
      await expect(page).toHaveURL(item.href);
    });
  }

  test("active tab shows aria-current=page after navigation", async ({ page }) => {
    await page.goto("/data");
    const dataTab = page.getByTestId("mobile-nav-data").first();
    await expect(dataTab).toHaveAttribute("aria-current", "page");
  });
});
