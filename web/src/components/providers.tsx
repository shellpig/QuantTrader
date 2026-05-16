"use client";

import { Toaster } from "sonner";
import { CommandPalette } from "@/components/command-palette";
import { ThemeProvider } from "@/components/theme-provider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider defaultTheme="dark" storageKey="qt-theme">
      {children}
      <Toaster
        position="bottom-right"
        duration={3000}
        richColors
        closeButton
      />
      <CommandPalette />
    </ThemeProvider>
  );
}
