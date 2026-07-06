import { backendBaseUrl } from "./api-client";

export type WorkflowEvent = {
  schema_version: string;
  event_id: string;
  event_type: string;
  source: string;
  run_id: string;
  thread_id: string;
  seq: number;
  step_id?: number;
  node_id?: string;
  node_name?: string;
  node_type?: string;
  status?: string;
  visible_input?: string;
  visible_output?: string;
  tool_name?: string;
  tool_calls?: Array<Record<string, unknown>>;
  artifacts?: Array<Record<string, unknown>>;
  metrics?: { duration_ms?: number; tokens?: number };
  error?: { code: string; message: string; retryable: boolean };
  started_at?: string;
  ended_at?: string;
};

export function streamEvents(
  runId: string,
  onEvent: (evt: WorkflowEvent) => void,
  onEnd: () => void
): EventSource {
  const es = new EventSource(`${backendBaseUrl()}/runs/${runId}/events`);
  es.onmessage = (msg) => {
    const data = JSON.parse(msg.data) as WorkflowEvent;
    onEvent(data);
  };
  es.addEventListener("end", () => {
    onEnd();
    es.close();
  });
  es.onerror = () => {
    onEnd();
    es.close();
  };
  return es;
}

