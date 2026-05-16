import { describe, it, expect } from "vitest";
import { readFileSync } from "fs";
import { resolve } from "path";

const REQUIRED_VARS = [
  "--background",
  "--foreground",
  "--primary",
  "--border",
  "--chart-up",
  "--chart-down",
];

const cssPath = resolve(__dirname, "../../app/globals.css");
const css = readFileSync(cssPath, "utf-8");

/** Extract the inner content of a CSS block matching `selector { ... }` */
function extractBlock(source: string, selectorPattern: RegExp): string {
  const re = new RegExp(selectorPattern.source + String.raw`\s*\{([^}]+)\}`, "s");
  return source.match(re)?.[1] ?? "";
}

describe("theme CSS variables", () => {
  it("light theme (:root) defines all required vars", () => {
    const block = extractBlock(css, /:root/);
    for (const v of REQUIRED_VARS) {
      expect(block, `${v} should be defined in :root`).toContain(v);
    }
  });

  it("explicit .light class defines all required vars", () => {
    const block = extractBlock(css, /\.light/);
    for (const v of REQUIRED_VARS) {
      expect(block, `${v} should be defined in .light`).toContain(v);
    }
  });

  it("dark theme (.dark) defines all required vars", () => {
    const block = extractBlock(css, /\.dark/);
    for (const v of REQUIRED_VARS) {
      expect(block, `${v} should be defined in .dark`).toContain(v);
    }
  });

  it("--chart-up and --chart-down have non-empty values in :root", () => {
    const block = extractBlock(css, /:root/);
    const upMatch = block.match(/--chart-up:\s*([^;]+);/);
    const downMatch = block.match(/--chart-down:\s*([^;]+);/);
    expect(upMatch?.[1]?.trim(), "--chart-up value should not be empty").toBeTruthy();
    expect(downMatch?.[1]?.trim(), "--chart-down value should not be empty").toBeTruthy();
  });
});
