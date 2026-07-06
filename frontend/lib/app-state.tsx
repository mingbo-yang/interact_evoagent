"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from "react";
import type { ReactNode } from "react";

import { approveRun, createRun, submitFeedback } from "@/lib/api-client";
import { streamEvents, type WorkflowEvent } from "@/lib/event-client";

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type Mode = "mock" | "evoagent";

type AppState = {
  messages: ChatMessage[];
  events: WorkflowEvent[];
  currentRunId: string | null;
  running: boolean;
  mode: Mode;
  selectedId?: string;
  elapsed: number;
  artifactKey: number;
  historyKey: number;
  approvalPending: boolean;
  approvalText: string;
  setMode: (m: Mode) => void;
  setSelectedId: (id?: string) => void;
  sendTask: (text: string) => Promise<void>;
  approve: (approved: boolean) => Promise<void>;
  feedback: (score: number, comment: string) => Promise<void>;
  openRun: (runId: string) => void;
};

const Ctx = createContext<AppState | null>(null);

const INITIAL_MSG: ChatMessage = {
  role: "assistant",
  content: "**EvoAgent Interactive Workflow** 已就绪。输入任务开始，右侧会实时显示工作流轨迹。"
};

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MSG]);
  const [events, setEvents] = useState<WorkflowEvent[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(undefined);
  const [running, setRunning] = useState(false);
  const [mode, setMode] = useState<Mode>("evoagent");
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const [artifactKey, setArtifactKey] = useState(0);
  const [historyKey, setHistoryKey] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  const seenSeq = useRef<Set<number>>(new Set());
  const sourceRef = useRef<EventSource | null>(null);
  const startRef = useRef<number>(0);

  useEffect(() => {
    if (!running) return;
    const t = setInterval(() => setElapsed(Date.now() - startRef.current), 200);
    return () => clearInterval(t);
  }, [running]);

  // Close the SSE stream only when the whole app unmounts.
  useEffect(() => {
    return () => sourceRef.current?.close();
  }, []);

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

  const addEvent = useCallback((evt: WorkflowEvent) => {
    if (seenSeq.current.has(evt.seq)) return;
    seenSeq.current.add(evt.seq);
    setEvents((prev) => [...prev, evt].sort((a, b) => a.seq - b.seq));
    if (evt.event_type === "artifact.created") setArtifactKey((k) => k + 1);
    if (evt.event_type === "node.completed" && evt.node_id === "final_response" && evt.visible_output) {
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
  }, []);

  const startStream = useCallback(
    (runId: string, resetTimer: boolean) => {
      if (resetTimer) {
        startRef.current = Date.now();
        setElapsed(0);
      }
      sourceRef.current?.close();
      sourceRef.current = streamEvents(runId, addEvent, () => {
        setRunning(false);
        setHistoryKey((k) => k + 1);
      });
    },
    [addEvent]
  );

  const sendTask = useCallback(
    async (text: string) => {
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
    },
    [mode, running, startStream]
  );

  const openRun = useCallback(
    (runId: string) => {
      if (running || runId === currentRunId) return;
      setCurrentRunId(runId);
      setEvents([]);
      seenSeq.current = new Set();
      setSelectedId(undefined);
      startRef.current = Date.now();
      setElapsed(0);
      setArtifactKey((k) => k + 1);
      startStream(runId, false);
    },
    [running, currentRunId, startStream]
  );

  const approve = useCallback(
    async (approved: boolean) => {
      if (currentRunId) await approveRun(currentRunId, approved);
    },
    [currentRunId]
  );

  const feedback = useCallback(
    async (score: number, comment: string) => {
      if (currentRunId) await submitFeedback(currentRunId, score, comment);
    },
    [currentRunId]
  );

  const value: AppState = {
    messages,
    events,
    currentRunId,
    running,
    mode,
    selectedId,
    elapsed,
    artifactKey,
    historyKey,
    approvalPending,
    approvalText,
    setMode,
    setSelectedId,
    sendTask,
    approve,
    feedback,
    openRun
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useAppState(): AppState {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useAppState must be used within AppStateProvider");
  return ctx;
}
