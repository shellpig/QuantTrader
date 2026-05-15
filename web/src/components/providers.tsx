"use client";

import { Toaster } from "sonner";
import { CommandPalette } from "@/components/command-palette";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        duration={3000}
        richColors
        closeButton
      />
      <CommandPalette />
    </>
  );
}
