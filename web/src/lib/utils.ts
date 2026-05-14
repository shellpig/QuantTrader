// Utility functions (Phase 10-B)
// shadcn/ui cn() + general helpers

import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

/** Merge Tailwind classes safely (shadcn/ui pattern). */
export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}
