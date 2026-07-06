"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import BottomTabs from "@/components/BottomTabs";
import ChatPanel, { type ChatMessage } from "@/components/ChatPanel";
import NodeDetailPanel from "@/components/NodeDetailPanel";
import RunHistory from "@/components/RunHistory";
import StatsBar from "@/components/StatsBar";
import TopNav from "@/components/TopNav";
import WorkflowPanel from "@/components/WorkflowPanel";
import { approveRun, createRun, submitFeedback } from "@/lib/api-client";
import { streamEvents, type WorkflowEvent } from "@/lib/event-client";

export default function Page() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    { role: "assistant", content: "**EvoAgent Interactive Workflow** 已就绪。输入任务开始，右侧会实时显示工作流轨迹。" }
  ]);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<"mock" | "evoagent">("mock");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [railCollapsed, setRailCollapsed] = useState(false);
  const [artifactKey, setArtifactKey] = useState(0);
  const [historyKey, setHistoryKey] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const seenSeq = useRef<Set<number>>(new Set());
  const sourceRef = useRef<EventSource | null>(null);
  const startRef = useRef<number>(0);

  // Live elapsed timer while a run is active.
  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 200);
    return () => clearInterval(t);
  }, [running]);

  const approvalPending = useMemo(() => {
    const relevant = events.filter(
      (e) => e.event_type === "user.approval.required" || e.event_type === "user.approval.received"
    );
    const last = relevant[relevant.length - 1];
    return Boolean(last && last.event_type === "user.approval.required");
  }, [events]);

  const approvalText = useMemo(() => {
    const req = [...events].reverse().find((e) => e.event_type === "user.approval.required");
    return req?.visible_output || "检测到高风险操作，是否允许执行？";
  }, [events]);

  const liveStats = useMemo(() => {
    const steps = new Set(
      events.filter((e) => e.event_type.startsWith("node.")).map((e) => `${e.node_id}:${e.step_id}`)
    ).size;
    const tools = events.filter((e) => e.event_type === "tool.completed").length;
    const last = events[events.length - 1];
    let status = running ? "running" : "idle";
    if (events.some((e) => e.event_type === "run.completed")) status = "completed";
    if (events.some((e) => e.event_type === "run.failed")) status = "failed";
    if (approvalPending) status = "paused";
    return { status, steps, tools, durationMs: elapsed, _last: last };
  }, [events, running, elapsed, approvalPending]);

  const selectedEvent = events.find((e) => e.event_id === selectedId);

  const addEvent = (evt: WorkflowEvent) => {
    if (seenSeq.current.has(evt.seq)) return;
    seenSeq.current.add(evt.seq);
    setEvents((prev) => [...prev, evt].sort((a, b) => a.seq - b.seq));
    if (evt.event_type === "artifact.created") setArtifactKey((k) => k + 1);
    if (
      evt.event_type === "node.completed" &&
      evt.node_id === "final_response" &&
      evt.visible_output
    ) {
      setMessages((prev) => [...prev, { role: "assistant", content: evt.visible_output! }]);
    }
    if (evt.event_type === "run.failed") {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `❌ **运行失败**: ${evt.error?.message || "unknown"}` }
      ]);
    }
    if (evt.event_type === "run.completed" || evt.event_type === "run.failed") {
      setHistoryKey((k) => k + 1);
    }
  };

  const startStream = (runId: string, resetTimer: boolean) => {
    if (resetTimer) {
      startRef.current = Date.now();
      setElapsed(0);
    }
    sourceRef.current?.close();
    sourceRef.current = streamEvents(runId, addEvent, () => {
      setRunning(false);
      setHistoryKey((k) => k + 1);
    });
  };

  const handleSend = async (text: string) => {
    if (!text.trim() || running) return;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setEvents([]);
    seenSeq.current = new Set();
    setSelectedId(undefined);
    setArtifactKey((k) => k + 1);
    setRunning(true);
    try {
      const run = await createRun(text, mode);
      setCurrentRunId(run.run_id);
      startStream(run.run_id, true);
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `❌ 无法创建 run: ${String(err)}` }]);
      setRunning(false);
    }
  };

  const handleOpenRun = (runId: string) => {
    if (running) return;
    setCurrentRunId(runId);
    setEvents([]);
    seenSeq.current = new Set();
    setSelectedId(undefined);
    startRef.current = Date.now();
    setElapsed(0);
    setArtifactKey((k) => k + 1);
    // Replay: the events endpoint streams the full history then closes.
    startStream(runId, false);
  };

  const handleApprove = async (approved: boolean) => {
    if (currentRunId) await approveRun(currentRunId, approved);
  };

  const handleFeedback = async (score: number, comment: string) => {
    if (currentRunId) await submitFeedback(currentRunId, score, comment);
  };

  return (
    <div className={`app ${railCollapsed ? "rail-collapsed" : ""}`}>
      <aside className="rail">
        <RunHistory activeRunId={currentRunId} refreshKey={historyKey} onOpenRun={handleOpenRun} />
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
            value={mode}
            onChange={(e) => setMode(e.target.value as "mock" | "evoagent")}
            disabled={running}
          >
            <option value="mock">mock orchestrator</option>
            <option value="evoagent">real evoagent</option>
          </select>
          {approvalPending ? <span className="badge paused">approval in chat ↓</span> : null}
        </header>

        <div className="body">
          <div className="chat-cell">
            <ChatPanel
              messages={messages}
              disabled={running}
              onSend={handleSend}
              approvalPending={approvalPending}
              approvalText={approvalText}
              onApprove={handleApprove}
            />
          </div>
          <div className="workflow-cell">
            <WorkflowPanel events={events} selectedId={selectedId} onSelect={(e) => setSelectedId(e.event_id)} />
          </div>
          <div className="bottom-cell" style={{ display: "grid", gridTemplateColumns: "0.9fr 1.1fr", gap: 14 }}>
            <NodeDetailPanel event={selectedEvent} />
            <BottomTabs
              events={events}
              runId={currentRunId}
              artifactRefreshKey={artifactKey}
              feedbackDisabled={running}
              onFeedback={handleFeedback}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
