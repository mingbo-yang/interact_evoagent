"use client";

import { useEffect, useState } from "react";

import { getStats, listRuns, type RunSummary, type Stats } from "@/lib/api-client";
import { fmtDuration } from "@/lib/ui";

type Props = {
  activeRunId: string | null;
  refreshKey: number;
  onOpenRun: (runId: string) => void;
};

export default function RunHistory({ activeRunId, refreshKey, onOpenRun }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);

  useEffect(() => {
    let cancelled = false;
    Promise.all([listRuns(40), getStats()])
      .then(([r, s]) => {
        if (!cancelled) {
          setRuns(r.runs);
          setStats(s);
        }
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [refreshKey]);

  return (
    <>
      <div className="rail-head">Overview</div>
      {stats ? (
        <div style={{ padding: "0 12px 10px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
          <MiniStat label="Runs" value={stats.total_runs} />
          <MiniStat label="Done" value={stats.completed} />
          <MiniStat label="Tools" value={stats.total_tools} />
          <MiniStat label="Memories" value={stats.total_memories} />
        </div>
      ) : null}

      <div className="rail-head">History</div>
      <div style={{ flex: 1, overflow: "auto", paddingBottom: 12 }}>
        {runs.length === 0 ? (
          <div className="empty">No runs yet.</div>
        ) : (
          runs.map((r) => (
            <div
              key={r.run_id}
              className={`run-item ${r.run_id === activeRunId ? "active" : ""}`}
              onClick={() => onOpenRun(r.run_id)}
            >
              <div className="rtitle">{r.user_input || "(empty)"}</div>
              <div className="rmeta">
                <span className={`badge ${statusClass(r.status)}`}>
                  <span className={`dot ${statusClass(r.status)}`} />
                  {r.status}
                </span>
                <span>{r.mode}</span>
                <span>{r.tool_count}🔧</span>
                <span>{fmtDuration(r.duration_ms)}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </>
  );
}

function statusClass(status: string): string {
  if (status === "completed") return "success";
  if (status === "failed") return "failed";
  if (status === "paused") return "paused";
  if (status === "running") return "running";
  return "waiting";
}

function MiniStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="stat" style={{ minWidth: 0 }}>
      <span className="v">{value}</span>
      <span className="k">{label}</span>
    </div>
  );
}
