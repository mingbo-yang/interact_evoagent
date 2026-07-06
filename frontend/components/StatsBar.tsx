"use client";

import { fmtDuration } from "@/lib/ui";

export type LiveStats = {
  status: string;
  steps: number;
  tools: number;
  durationMs: number;
};

type Props = {
  live: LiveStats;
};

export default function StatsBar({ live }: Props) {
  return (
    <div className="stats">
      <div className="stat">
        <span className="v">{live.steps}</span>
        <span className="k">steps</span>
      </div>
      <div className="stat">
        <span className="v">{live.tools}</span>
        <span className="k">tools</span>
      </div>
      <div className="stat">
        <span className="v">{fmtDuration(live.durationMs)}</span>
        <span className="k">elapsed</span>
      </div>
      <div className="stat">
        <span className="v" style={{ textTransform: "capitalize" }}>{live.status}</span>
        <span className="k">status</span>
      </div>
    </div>
  );
}
