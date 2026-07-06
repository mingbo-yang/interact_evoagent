import type { WorkflowEvent } from "./event-client";

const NODE_ICONS: Record<string, string> = {
  task_understanding: "🧠",
  memory_retrieval: "📚",
  planning: "🗺️",
  tool_routing: "🔀",
  execution: "⚙️",
  reflection: "🔎",
  memory_update: "💾",
  skill_evolution: "✨",
  final_response: "✅"
};

const EVENT_ICONS: Record<string, string> = {
  "run.started": "🚀",
  "run.completed": "🏁",
  "run.failed": "💥",
  "tool.started": "🔧",
  "tool.completed": "🔧",
  "tool.failed": "🔧",
  "artifact.created": "📦",
  "memory.updated": "💾",
  "user.approval.required": "⏸️",
  "user.approval.received": "▶️"
};

const TOOL_ICONS: Record<string, string> = {
  shell: "💻",
  bash: "💻",
  write_file: "📝",
  edit_file: "✏️",
  multi_edit: "✏️",
  apply_patch: "🩹",
  read_file: "📄",
  run_tests: "🧪",
  git_diff: "🔀",
  git_status: "🌿",
  python: "🐍",
  web_search: "🌐",
  web_fetch: "🌐"
};

export function nodeIcon(evt: WorkflowEvent): string {
  if (evt.node_type && NODE_ICONS[evt.node_type]) {
    return NODE_ICONS[evt.node_type];
  }
  if (evt.tool_name) {
    return TOOL_ICONS[evt.tool_name] || "🔧";
  }
  return EVENT_ICONS[evt.event_type] || "•";
}

export function toolIcon(name?: string): string {
  if (!name) return "🔧";
  return TOOL_ICONS[name] || "🔧";
}

export function statusOf(evt: WorkflowEvent): string {
  return evt.status || "waiting";
}

export function fmtDuration(ms?: number): string {
  if (!ms || ms <= 0) return "—";
  if (ms < 1000) return `${ms}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

export function fmtTime(iso?: string): string {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleTimeString();
  } catch {
    return iso;
  }
}
