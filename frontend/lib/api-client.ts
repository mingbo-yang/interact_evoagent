export type RunCreateResponse = {
  run_id: string;
  thread_id: string;
  status: string;
};

export type RunSummary = {
  run_id: string;
  thread_id: string;
  mode: string;
  status: string;
  user_input: string;
  tool_count: number;
  event_count: number;
  duration_ms: number;
  created_at: string;
  updated_at: string;
};

export type Stats = {
  total_runs: number;
  completed: number;
  failed: number;
  total_tools: number;
  total_events: number;
  avg_duration_ms: number;
  total_memories: number;
  total_artifacts: number;
};

export type Artifact = {
  id: number;
  kind: string;
  title: string;
  content: string;
  created_at: string;
};

const BASE_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, init);
  if (!res.ok) {
    throw new Error(`Request failed ${res.status}: ${path}`);
  }
  return res.json();
}

export function createRun(message: string, mode: "mock" | "evoagent"): Promise<RunCreateResponse> {
  return jsonFetch("/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, mode })
  });
}

export async function approveRun(runId: string, approved: boolean): Promise<void> {
  await jsonFetch(`/runs/${runId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ approved })
  });
}

export async function submitFeedback(runId: string, score: number, comment: string): Promise<void> {
  await jsonFetch(`/runs/${runId}/feedback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ score, comment })
  });
}

export function listRuns(limit = 50): Promise<{ runs: RunSummary[] }> {
  return jsonFetch(`/runs?limit=${limit}`);
}

export function getStats(): Promise<Stats> {
  return jsonFetch("/stats");
}

export function listArtifacts(runId: string): Promise<{ artifacts: Artifact[] }> {
  return jsonFetch(`/runs/${runId}/artifacts`);
}

export function getEventsList(runId: string): Promise<{ events: any[] }> {
  return jsonFetch(`/runs/${runId}/events/list`);
}

export function backendBaseUrl(): string {
  return BASE_URL;
}
