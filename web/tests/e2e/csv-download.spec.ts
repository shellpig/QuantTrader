import { test, expect } from "@playwright/test";

/**
 * E2E smoke: batch compare CSV download
 * Requires API server running at localhost:8000 with 2330 data available.
 */
test.describe("CSV download", () => {
  test.use({ viewport: { width: 1280, height: 800 } });

  test("batch compare completes and CSV download is triggered", async ({ page }) => {
    await page.goto("/backtest");

    // Switch to batch compare tab
    const batchTab = page.locator('[data-testid="tab-batch"]');
    await expect(batchTab).toBeVisible({ timeout: 10_000 });
    await batchTab.click();

    // Fill symbol and press Enter to confirm
    const symbolInput = page.locator('[data-testid="stock-selector-input"]').first();
    await symbolInput.fill("2330");
    await symbolInput.press("Enter");

    // Fill dates
    const startInput = page.locator('[data-testid="start-date-input"]').first();
    await startInput.fill("2023-01-01");
    const endInput = page.locator('[data-testid="end-date-input"]').first();
    await endInput.fill("2023-12-31");

    // Wait for strategy presets to load, then select RSI_14 (index 1, non-DCA strategy)
    const rsi14Option = page.locator('[data-testid="strategy-option-1"]');
    await expect(rsi14Option).toBeVisible({ timeout: 10_000 });
    // Use click() for React controlled checkbox to avoid state-check race
    await rsi14Option.click();

    // Run batch compare
    const runButton = page.locator('[data-testid="start-batch-btn"]');
    await expect(runButton).toBeEnabled({ timeout: 5_000 });
    await runButton.click();

    // Wait for comparison table
    const compTable = page.locator('[data-testid="comparison-table"]');
    await expect(compTable).toBeVisible({ timeout: 60_000 });

    // Listen for download then click CSV button
    const downloadPromise = page.waitForEvent("download", { timeout: 10_000 });
    const csvButton = page.locator('[data-testid="download-batch-csv-btn"]');
    await expect(csvButton).toBeEnabled({ timeout: 5_000 });
    await csvButton.click();
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toMatch(/\.csv$/);
  });
});
