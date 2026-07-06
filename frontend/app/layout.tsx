import "./globals.css";
import "reactflow/dist/style.css";
import type { ReactNode } from "react";

import { AppStateProvider } from "@/lib/app-state";

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="zh-CN">
      <body>
        <AppStateProvider>{children}</AppStateProvider>
      </body>
    </html>
  );
}

