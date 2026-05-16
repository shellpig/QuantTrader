import { defineConfig, devices } from "@playwright/test";

/**
 * Playwright E2E smoke config (Phase 10-H-1)
 * Run manually: cd web && pnpm exec playwright test
 *
 * Requires both servers running before exec:
 *   API:  uvicorn api.main:app --port 8000
 *   Web:  pnpm dev (port 3000)
 */
export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  retries: 0,
  workers: 1,
  reporter: "list",
  timeout: 60_000,
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
    actionTimeout: 15_000,
  },
  projects: [
    {
      name: "desktop-chromium",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1280, height: 800 },
      },
    },
    {
      name: "mobile-chromium",
      use: {
        ...devices["Pixel 5"],
      },
    },
  ],
});
