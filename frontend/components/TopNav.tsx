"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

export default function TopNav() {
  const path = usePathname();
  const is = (p: string) => (p === "/" ? path === "/" : path.startsWith(p));
  return (
    <div className="brand" style={{ gap: 14 }}>
      <span className="logo">◆</span>
      <span>
        EvoAgent
        <small>Interactive Workflow</small>
      </span>
      <nav className="nav" style={{ marginLeft: 10 }}>
        <Link href="/" className={is("/") ? "active" : ""}>🖥️ Console</Link>
        <Link href="/flow" className={is("/flow") ? "active" : ""}>🧩 Flow</Link>
        <Link href="/metrics" className={is("/metrics") ? "active" : ""}>📊 Metrics</Link>
      </nav>
    </div>
  );
}
