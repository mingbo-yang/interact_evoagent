"use client";

import type { WorkflowEvent } from "@/lib/event-client";
import { fmtDuration, fmtTime, nodeIcon, statusOf } from "@/lib/ui";

type Props = {
  event?: WorkflowEvent;
};

export default function NodeDetailPanel({ event }: Props) {
  if (!event) {
    return (
      <div className="panel" style={{ height: "100%" }}>
        <div className="panel-head">
          <span className="icon">🔬</span> Node Detail
        </div>
        <div className="panel-body">
          <div className="empty">Click a workflow step to inspect its input, output and metrics.</div>
        </div>
      </div>
    );
  }

  const st = statusOf(event);
  return (
    <div className="panel" style={{ height: "100%" }}>
      <div className="panel-head">
        <span className="icon">{nodeIcon(event)}</span>
        {event.node_name || event.tool_name || event.event_type}
        <span className={`badge ${st}`} style={{ marginLeft: "auto" }}>
          <span className={`dot ${st}`} />
          {st}
        </span>
      </div>
      <div className="panel-body">
        <div className="detail">
          <div className="kv">
            <div className="k">Event</div>
            <div className="v">{event.event_type}</div>
            <div className="k">Seq</div>
            <div className="v">#{event.seq}</div>
            {event.node_type ? (
              <>
                <div className="k">Node type</div>
                <div className="v">{event.node_type}</div>
              </>
            ) : null}
            {event.tool_name ? (
              <>
                <div className="k">Tool</div>
                <div className="v">{event.tool_name}</div>
              </>
            ) : null}
            <div className="k">Source</div>
            <div className="v">{event.source}</div>
            {event.metrics?.duration_ms ? (
              <>
                <div className="k">Duration</div>
                <div className="v">{fmtDuration(event.metrics.duration_ms)}</div>
              </>
            ) : null}
            <div className="k">Started</div>
            <div className="v">{fmtTime(event.started_at)}</div>
            {event.ended_at ? (
              <>
                <div className="k">Ended</div>
                <div className="v">{fmtTime(event.ended_at)}</div>
              </>
            ) : null}
          </div>

          {event.visible_input ? (
            <div className="block">
              <div className="block-title">Visible input</div>
              <pre>{event.visible_input}</pre>
            </div>
          ) : null}
          {event.visible_output ? (
            <div className="block">
              <div className="block-title">Visible output</div>
              <pre>{event.visible_output}</pre>
            </div>
          ) : null}
          {event.error ? (
            <div className="block" style={{ borderColor: "rgba(248,113,113,0.4)" }}>
              <div className="block-title" style={{ color: "var(--danger)" }}>
                Error · {event.error.code}
              </div>
              <pre>{event.error.message}</pre>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
