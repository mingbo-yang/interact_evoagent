"use client";

import { useMemo, useState } from "react";

import BottomTabs from "@/components/BottomTabs";
import ChatPanel from "@/components/ChatPanel";
import NodeDetailPanel from "@/components/NodeDetailPanel";
import RunHistory from "@/components/RunHistory";
import StatsBar from "@/components/StatsBar";
import TopNav from "@/components/TopNav";
import WorkflowPanel from "@/components/WorkflowPanel";
import { useAppState } from "@/lib/app-state";

export default function Page() {
  const app = useAppState();
  const [railCollapsed, setRailCollapsed] = useState(false);

  const liveStats = useMemo(() => {
    const steps = new Set(
      app.events.filter((e) => e.event_type.startsWith("node.")).map((e) => `${e.node_id}:${e.step_id}`)
    ).size;
    const tools = app.events.filter((e) => e.event_type === "tool.completed").length;
    let status = app.running ? "running" : "idle";
    if (app.events.some((e) => e.event_type === "run.completed")) status = "completed";
    if (app.events.some((e) => e.event_type === "run.failed")) status = "failed";
    if (app.approvalPending) status = "paused";
    return { status, steps, tools, durationMs: app.elapsed };
  }, [app.events, app.running, app.elapsed, app.approvalPending]);

  const selectedEvent = app.events.find((e) => e.event_id === app.selectedId);

  return (
    <div className={`app ${railCollapsed ? "rail-collapsed" : ""}`}>
      <aside className="rail">
        <RunHistory activeRunId={app.currentRunId} refreshKey={app.historyKey} onOpenRun={app.openRun} />
      </aside>

      <div className="main">
        <header className="header">
          <button className="rail-toggle" onClick={() => setRailCollapsed((v) => !v)} title="Toggle history">
            ☰
          </button>
          <TopNav />
          <StatsBar live={liveStats} />
          <div className="header-spacer" />
          <select
            className="select"
            value={app.mode}
            onChange={(e) => app.setMode(e.target.value as "mock" | "evoagent")}
            disabled={app.running}
          >
            <option value="evoagent">real evoagent</option>
            <option value="mock">mock orchestrator</option>
          </select>
          {app.approvalPending ? <span className="badge paused">approval in chat ↓</span> : null}
        </header>

        <div className="body">
          <div className="chat-cell">
            <ChatPanel
              messages={app.messages}
              disabled={app.running}
              onSend={app.sendTask}
              approvalPending={app.approvalPending}
              approvalText={app.approvalText}
              onApprove={app.approve}
            />
          </div>
          <div className="workflow-cell">
            <WorkflowPanel
              events={app.events}
              selectedId={app.selectedId}
              onSelect={(e) => app.setSelectedId(e.event_id)}
            />
          </div>
          <div className="bottom-cell" style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: 14 }}>
            <NodeDetailPanel event={selectedEvent} />
            <BottomTabs
              events={app.events}
              runId={app.currentRunId}
              artifactRefreshKey={app.artifactKey}
              feedbackDisabled={app.running}
              onFeedback={app.feedback}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
