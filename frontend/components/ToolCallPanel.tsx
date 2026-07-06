"use client";

import type { WorkflowEvent } from "@/lib/event-client";
import { fmtDuration, statusOf, toolIcon } from "@/lib/ui";

type Props = {
  events: WorkflowEvent[];
};

export default function ToolCallPanel({ events }: Props) {
  const toolEvents = events.filter((e) => e.event_type.startsWith("tool."));
  if (toolEvents.length === 0) {
    return <div className="empty">No tool calls yet.</div>;
  }
  return (
    <div>
      {toolEvents.map((e) => {
        const st = statusOf(e);
        return (
          <div key={e.event_id} className="card">
            <div className="card-head">
              <span className="tool-icon">{toolIcon(e.tool_name)}</span>
              <span>{e.tool_name || "tool"}</span>
              <span className="src">{e.source}</span>
              <span className={`badge ${st}`} style={{ marginLeft: "auto" }}>
                <span className={`dot ${st}`} />
                {st}
              </span>
            </div>
            <div className="tl-meta">
              #{e.seq} · {e.event_type}
              {e.metrics?.duration_ms ? ` · ${fmtDuration(e.metrics.duration_ms)}` : ""}
            </div>
            {e.visible_input ? (
              <pre style={{ color: "var(--accent)" }}>$ {e.visible_input}</pre>
            ) : null}
            {e.visible_output ? <pre>{e.visible_output}</pre> : null}
            {e.error ? <pre style={{ color: "var(--danger)" }}>{e.error.message}</pre> : null}
          </div>
        );
      })}
    </div>
  );
}
