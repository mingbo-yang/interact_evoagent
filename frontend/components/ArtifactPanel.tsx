"use client";

import { useEffect, useState } from "react";

import { listArtifacts, type Artifact } from "@/lib/api-client";
import DiffViewer from "./DiffViewer";

type Props = {
  runId: string | null;
  refreshKey: number;
};

export default function ArtifactPanel({ runId, refreshKey }: Props) {
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [openId, setOpenId] = useState<number | null>(null);

  useEffect(() => {
    let cancelled = false;
    if (!runId) {
      setArtifacts([]);
      return;
    }
    listArtifacts(runId)
      .then((r) => {
        if (!cancelled) setArtifacts(r.artifacts);
      })
      .catch(() => {
        if (!cancelled) setArtifacts([]);
      });
    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  if (!runId || artifacts.length === 0) {
    return <div className="empty">No artifacts yet.</div>;
  }

  return (
    <div>
      {artifacts.map((a) => {
        const open = openId === a.id;
        const isDiff = a.kind === "git_diff" || a.content.startsWith("diff ") || a.content.includes("@@");
        return (
          <div key={a.id} className="card">
            <div
              className="card-head"
              style={{ cursor: "pointer" }}
              onClick={() => setOpenId(open ? null : a.id)}
            >
              <span className="tool-icon">{a.kind === "git_diff" ? "🔀" : a.kind === "run_tests" ? "🧪" : "📦"}</span>
              <span>{a.title}</span>
              <span className="src">{a.kind}</span>
              <span style={{ marginLeft: "auto", color: "var(--text-faint)", fontSize: 11 }}>
                {open ? "▲" : "▼"}
              </span>
            </div>
            {open ? (
              isDiff ? (
                <div style={{ marginTop: 8 }}>
                  <DiffViewer text={a.content} />
                </div>
              ) : (
                <pre>{a.content}</pre>
              )
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
