"use client";

import { useEffect, useRef, useState } from "react";

import FlowGraph from "@/components/FlowGraph";
import RunSelector from "@/components/RunSelector";
import TopNav from "@/components/TopNav";
import { streamEvents, type WorkflowEvent } from "@/lib/event-client";

export default function FlowPage() {
  const [runId, setRunId] = useState<string | null>(null);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [running, setRunning] = useState(false);
  const seen = useRef<Set<number>>(new Set());
  const src = useRef<EventSource | null>(null);

  const openRun = (id: string) => {
    setRunId(id);
    setEvents([]);
    seen.current = new Set();
    setRunning(true);
    src.current?.close();
    src.current = streamEvents(
      id,
      (evt) => {
        if (seen.current.has(evt.seq)) return;
        seen.current.add(evt.seq);
        setEvents((prev) => [...prev, evt].sort((a, b) => a.seq - b.seq));
      },
      () => setRunning(false)
    );
  };

  useEffect(() => {
    return () => {
      src.current?.close();
    };
  }, []);

  return (
    <div className="page-shell">
      <header className="header">
        <TopNav />
        <div className="header-spacer" />
        <span className="meta" style={{ color: "var(--text-faint)", fontSize: 12 }}>
          workflow as flowchart{running ? " · live" : ""}
        </span>
        <RunSelector value={runId} onChange={openRun} />
      </header>
      <div className="page-content">
        {runId ? (
          <FlowGraph events={events} running={running} />
        ) : (
          <div className="flow-wrap">
            <div className="empty" style={{ paddingTop: 120 }}>
              选择一个运行以查看其工作流流程图。
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
