import type { Edge, Node } from "reactflow";

import type { WorkflowEvent } from "./event-client";
import { nodeIcon } from "./ui";

export type FlowData = { nodes: Node[]; edges: Edge[]; activeStep: number };

type StageAgg = {
  node_id: string;
  node_name: string;
  node_type: string;
  step_id: number;
  status: string;
  duration?: number;
  icon: string;
};

const COL = 230;
const ROW = 150;

// Build a reactflow graph (pipeline + tool lane) from an ordered event list.
export function buildFlow(events: WorkflowEvent[], running: boolean): FlowData {
  const sorted = [...events].sort((a, b) => a.seq - b.seq);

  // Aggregate pipeline stages by node_id (keep the most advanced status).
  const stageMap = new Map<string, StageAgg>();
  const stageOrder: string[] = [];
  for (const e of sorted) {
    if (!e.node_id || !e.event_type.startsWith("node.")) continue;
    const existing = stageMap.get(e.node_id);
    const status = e.status || "waiting";
    if (!existing) {
      stageMap.set(e.node_id, {
        node_id: e.node_id,
        node_name: e.node_name || e.node_id,
        node_type: e.node_type || "",
        step_id: e.step_id || stageOrder.length + 1,
        status,
        duration: e.metrics?.duration_ms,
        icon: nodeIcon(e)
      });
      stageOrder.push(e.node_id);
    } else {
      existing.status = status;
      if (e.metrics?.duration_ms) existing.duration = e.metrics.duration_ms;
    }
  }
  const stages = stageOrder.map((id) => stageMap.get(id)!).sort((a, b) => a.step_id - b.step_id);

  // Tool calls (group by tool name + started seq) -> lane nodes.
  const tools: { id: string; name: string; status: string; icon: string; seq: number }[] = [];
  const toolSeen = new Map<string, number>();
  for (const e of sorted) {
    if (!e.event_type.startsWith("tool.")) continue;
    const key = `${e.tool_name}`;
    const status = e.status || "waiting";
    const existingIdx = toolSeen.get(`${e.tool_name}:${e.seq > 0 ? "x" : ""}`);
    // Group consecutive events of the same tool into one node by name occurrence.
    const idx = tools.findIndex((t) => t.name === e.tool_name && Math.abs(t.seq - e.seq) < 6);
    if (idx === -1) {
      tools.push({ id: `tool_${e.event_id}`, name: e.tool_name || "tool", status, icon: nodeIcon(e), seq: e.seq });
    } else {
      tools[idx].status = status;
    }
    void existingIdx;
    void key;
  }

  const nodes: Node[] = [];
  const edges: Edge[] = [];

  const hasStart = sorted.some((e) => e.event_type === "run.started");
  const endEvt = sorted.find((e) => e.event_type === "run.completed" || e.event_type === "run.failed");

  let x = 0;
  if (hasStart) {
    nodes.push({
      id: "start",
      type: "fnode",
      position: { x, y: 0 },
      data: { icon: "🚀", name: "Run started", sub: "run.started", status: "success" }
    });
    x += COL;
  }

  let activeStep = -1;
  stages.forEach((s, i) => {
    const id = `stage_${s.node_id}`;
    nodes.push({
      id,
      type: "fnode",
      position: { x, y: 0 },
      data: {
        icon: s.icon,
        name: s.node_name,
        sub: s.duration ? `${(s.duration / 1000).toFixed(1)}s · #${s.step_id}` : `step ${s.step_id}`,
        status: s.status
      }
    });
    if (s.status === "running") activeStep = i;
    const prev = i === 0 ? (hasStart ? "start" : null) : `stage_${stages[i - 1].node_id}`;
    if (prev) {
      edges.push({
        id: `e_${prev}_${id}`,
        source: prev,
        target: id,
        animated: running && (s.status === "running" || s.status === "waiting"),
        style: { stroke: edgeColor(s.status), strokeWidth: 2 }
      });
    }
    x += COL;
  });

  // End node.
  if (endEvt) {
    nodes.push({
      id: "end",
      type: "fnode",
      position: { x, y: 0 },
      data: {
        icon: endEvt.event_type === "run.failed" ? "💥" : "🏁",
        name: endEvt.event_type === "run.failed" ? "Run failed" : "Run completed",
        sub: endEvt.event_type,
        status: endEvt.event_type === "run.failed" ? "failed" : "success"
      }
    });
    const last = stages.length ? `stage_${stages[stages.length - 1].node_id}` : hasStart ? "start" : null;
    if (last) {
      edges.push({
        id: `e_${last}_end`,
        source: last,
        target: "end",
        animated: false,
        style: { stroke: edgeColor(endEvt.event_type === "run.failed" ? "failed" : "success"), strokeWidth: 2 }
      });
    }
  }

  // Tool lane under the execution stage (or centered).
  const execIdx = stages.findIndex((s) => s.node_type === "execution" || s.node_id === "execution");
  const execX = (hasStart ? 1 : 0) + (execIdx >= 0 ? execIdx : Math.max(0, stages.length - 1));
  tools.forEach((t, i) => {
    const id = t.id;
    nodes.push({
      id,
      type: "fnode",
      position: { x: (execX + i) * COL, y: ROW },
      data: { icon: t.icon, name: t.name, sub: "tool call", status: t.status }
    });
    const src = execIdx >= 0 ? `stage_${stages[execIdx].node_id}` : "start";
    if (nodes.some((n) => n.id === src)) {
      edges.push({
        id: `et_${src}_${id}`,
        source: src,
        target: id,
        animated: running && t.status === "running",
        style: { stroke: edgeColor(t.status), strokeWidth: 1.5, strokeDasharray: "4 3" }
      });
    }
  });

  return { nodes, edges, activeStep };
}

function edgeColor(status: string): string {
  switch (status) {
    case "success":
      return "#34d399";
    case "failed":
      return "#f87171";
    case "running":
      return "#60a5fa";
    case "paused":
      return "#fbbf24";
    default:
      return "#3a4a70";
  }
}
