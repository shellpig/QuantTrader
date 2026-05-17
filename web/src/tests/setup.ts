// Vitest setup (Phase 10-B)
import { afterEach } from "vitest";
import "@testing-library/jest-dom";

// ResizeObserver is not available in jsdom; stub it for Radix UI components.
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Clear localStorage between tests so effects (e.g. qt-last-symbol) don't leak across cases.
afterEach(() => {
  localStorage.clear();
});
