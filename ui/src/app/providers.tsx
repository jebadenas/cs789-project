"use client";

import type React from "react";
import { BaseStyles, ThemeProvider } from "@primer/react";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider colorMode="light">
      <BaseStyles>{children}</BaseStyles>
    </ThemeProvider>
  );
}
