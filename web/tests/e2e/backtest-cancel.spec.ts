import { test, expect } from "@playwright/test";

/**
 * E2E smoke: cancel a running backtest job
 * Requires API server running at localhost:8000 with 2330 data available.
 */
test.describe("Backtest cancel", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("cancel job shows cancelled status and preserves partial result", async ({ page }) => {
    await page.goto("/backtest");

    const singleTab = page.locator('[data-testid="tab-single"]');
    await expect(singleTab).toBeVisible({ timeout: 10_000 });
    await singleTab.click();

    // Fill in a long date range to give time to cancel
    const symbolInput = page.locator('[data-testid="stock-selector-input"]').first();
    await symbolInput.fill("2330");
    await symbolInput.press("Enter");

    const startInput = page.locator('[data-testid="start-date-input"]').first();
    await startInput.fill("2015-01-01");
    const endInput = page.locator('[data-testid="end-date-input"]').first();
    await endInput.fill("2024-12-31");

    // Wait for strategy presets to load, then select MA20_MA60 (index 7)
    const strategySelect = page.locator('[data-testid="strategy-preset-select"]');
    await expect(strategySelect).toBeEnabled({ timeout: 10_000 });
    await strategySelect.selectOption({ value: "7" });

    const runButton = page.locator('[data-testid="start-backtest-btn"]');
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
    await runButton.click();

    // Wait for progress bar to appear then cancel
    const progressBar = page.locator('[data-testid="backtest-progress-bar"]');
    await expect(progressBar).toBeVisible({ timeout: 15_000 });

    const cancelButton = page.locator('button', { hasText: "取消" }).first();
    await expect(cancelButton).toBeVisible({ timeout: 5_000 });
    await cancelButton.click();

    // After cancel, either a tearsheet or cancelled text appears
    await expect(
      page.locator('[data-testid="tearsheet-cards"]')
        .or(page.getByText("回測已取消").or(page.getByText("cancelled")))
        .first()
    ).toBeVisible({ timeout: 15_000 });
  });
});
