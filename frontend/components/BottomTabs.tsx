"use client";

import { useState } from "react";

import type { WorkflowEvent } from "@/lib/event-client";
import ArtifactPanel from "./ArtifactPanel";
import FeedbackPanel from "./FeedbackPanel";
import ToolCallPanel from "./ToolCallPanel";

type Props = {
  events: WorkflowEvent[];
  runId: string | null;
  artifactRefreshKey: number;
  feedbackDisabled: boolean;
  onFeedback: (score: number, comment: string) => Promise<void>;
};

type Tab = "tools" | "artifacts" | "feedback";

export default function BottomTabs({
  events,
  runId,
  artifactRefreshKey,
  feedbackDisabled,
  onFeedback
}: Props) {
  const [tab, setTab] = useState<Tab>("tools");
  const toolCount = events.filter((e) => e.event_type.startsWith("tool.")).length;
  const artifactCount = events.filter((e) => e.event_type === "artifact.created").length;

  return (
    <div className="panel" style={{ height: "100%" }}>
      <div className="tabs">
        <div className={`tab ${tab === "tools" ? "active" : ""}`} onClick={() => setTab("tools")}>
          🔧 Tool Calls <span className="pill">{toolCount}</span>
        </div>
        <div className={`tab ${tab === "artifacts" ? "active" : ""}`} onClick={() => setTab("artifacts")}>
          📦 Artifacts <span className="pill">{artifactCount}</span>
        </div>
        <div className={`tab ${tab === "feedback" ? "active" : ""}`} onClick={() => setTab("feedback")}>
          ⭐ Feedback
        </div>
      </div>
      <div className="panel-body">
        {tab === "tools" ? <ToolCallPanel events={events} /> : null}
        {tab === "artifacts" ? <ArtifactPanel runId={runId} refreshKey={artifactRefreshKey} /> : null}
        {tab === "feedback" ? (
          <FeedbackPanel runId={runId} disabled={feedbackDisabled} onSubmit={onFeedback} />
        ) : null}
      </div>
    </div>
  );
}
