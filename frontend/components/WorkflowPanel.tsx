"use client";

import type { WorkflowEvent } from "@/lib/event-client";
import { fmtDuration, nodeIcon, statusOf } from "@/lib/ui";

type Props = {
  events: WorkflowEvent[];
  selectedId?: string;
  onSelect: (evt: WorkflowEvent) => void;
};

// Collapse node.started/node.completed pairs: prefer the completed event, but
// show a running node if it hasn't completed yet.
function collapse(events: WorkflowEvent[]): WorkflowEvent[] {
  const byNode = new Map<string, WorkflowEvent>();
  const order: WorkflowEvent[] = [];
  for (const e of events) {
    const key = e.node_id ? `node:${e.node_id}:${e.step_id}` : `evt:${e.event_id}`;
    if (e.event_type.startsWith("node.")) {
      const existing = byNode.get(key);
      if (!existing) {
        byNode.set(key, e);
        order.push(e);
      } else {
        // replace with the more advanced state (completed/failed over started)
        const idx = order.indexOf(existing);
        if (idx >= 0) order[idx] = e;
        byNode.set(key, e);
      }
    } else {
      order.push(e);
    }
  }
  return order;
}

export default function WorkflowPanel({ events, selectedId, onSelect }: Props) {
  const nodes = collapse(events);
  const maxDur = Math.max(1, ...nodes.map((n) => n.metrics?.duration_ms || 0));

  return (
    <div className="panel workflow-cell" style={{ height: "100%" }}>
      <div className="panel-head">
        <span className="icon">🧭</span> Workflow Trace
        <span className="count">{nodes.length} steps</span>
      </div>
      <div className="panel-body">
        {nodes.length === 0 ? (
          <div className="empty">Send a task to see the live workflow trace.</div>
        ) : (
          <div className="timeline">
            {nodes.map((evt, i) => {
              const st = statusOf(evt);
              const dur = evt.metrics?.duration_ms || 0;
              const active = evt.event_id === selectedId;
              return (
                <div
                  key={evt.event_id}
                  className={`tl-node st-${st} ${active ? "active" : ""}`}
                  onClick={() => onSelect(evt)}
                >
                  <div className="tl-rail">
                    <div className="tl-glyph">{nodeIcon(evt)}</div>
                    {i < nodes.length - 1 ? <div className="tl-line" /> : null}
                  </div>
                  <div className="tl-body">
                    <div className="tl-title">
                      <span className="name">
                        {evt.node_name || evt.tool_name || evt.event_type}
                      </span>
                      <span className={`badge ${st}`}>
                        <span className={`dot ${st}`} />
                        {st}
                      </span>
                    </div>
                    <div className="tl-meta">
                      #{evt.seq} · {evt.event_type}
                      {evt.tool_name ? ` · ${evt.tool_name}` : ""}
                      {dur ? ` · ${fmtDuration(dur)}` : ""}
                      {evt.source === "evoagent" ? " · evoagent" : ""}
                    </div>
                    {evt.visible_output ? (
                      <div className="tl-out">{evt.visible_output}</div>
                    ) : null}
                    {evt.error ? (
                      <div className="tl-out" style={{ color: "var(--danger)" }}>
                        {evt.error.message}
                      </div>
                    ) : null}
                    {dur ? (
                      <span
                        className="tl-dur"
                        style={{ width: `${Math.max(12, (dur / maxDur) * 120)}px` }}
                      />
                    ) : null}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
