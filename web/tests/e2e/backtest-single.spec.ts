import { test, expect } from "@playwright/test";

/**
 * E2E smoke: single backtest job
 * Requires API server running at localhost:8000 with 2330 data available.
 */
test.describe("Single backtest", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("runs backtest job and shows tearsheet metric cards", async ({ page }) => {
    await page.goto("/backtest");

    // Ensure Single Run tab is active
    const singleTab = page.locator('[data-testid="tab-single"]');
    await expect(singleTab).toBeVisible({ timeout: 10_000 });
    await singleTab.click();

    // Fill in symbol (StockSelector confirms on Enter)
    const symbolInput = page.locator('[data-testid="stock-selector-input"]').first();
    await symbolInput.fill("2330");
    await symbolInput.press("Enter");

    // Fill start / end date
    const startInput = page.locator('[data-testid="start-date-input"]').first();
    await startInput.fill("2023-01-01");
    const endInput = page.locator('[data-testid="end-date-input"]').first();
    await endInput.fill("2023-12-31");

    // Wait for strategy presets to load, then select MA20_MA60 (index 7) to avoid DCA timezone bug
    const strategySelect = page.locator('[data-testid="strategy-preset-select"]');
    await expect(strategySelect).toBeEnabled({ timeout: 10_000 });
    await strategySelect.selectOption({ value: "7" });

    // Submit
    const runButton = page.locator('[data-testid="start-backtest-btn"]');
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
    await runButton.click();

    // Wait for progress or result
    await expect(
      page.locator('[data-testid="backtest-progress-bar"]').or(page.locator('[data-testid="tearsheet-cards"]'))
    ).toBeVisible({ timeout: 30_000 });

    // Wait for tearsheet (metric cards)
    const tearsheet = page.locator('[data-testid="tearsheet-cards"]');
    await expect(tearsheet).toBeVisible({ timeout: 60_000 });

    // Verify at least 5 metric values rendered
    const metricValues = tearsheet.locator('[data-testid="metric-value"]');
    await expect(metricValues).toHaveCount(5, { timeout: 10_000 });

    // Equity curve should also be visible
    const equity = page.locator('[data-testid="equity-curve-chart"]').first();
    await expect(equity).toBeVisible({ timeout: 10_000 });
  });
});
