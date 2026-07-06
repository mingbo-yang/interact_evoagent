"use client";

import { useEffect, useState } from "react";

import { listRuns, type RunSummary } from "@/lib/api-client";

type Props = {
  value: string | null;
  onChange: (runId: string) => void;
  refreshKey?: number;
};

export default function RunSelector({ value, onChange, refreshKey }: Props) {
  const [runs, setRuns] = useState<RunSummary[]>([]);

  useEffect(() => {
    let cancelled = false;
    listRuns(40)
      .then((r) => {
        if (cancelled) return;
        setRuns(r.runs);
        if (!value && r.runs.length > 0) onChange(r.runs[0].run_id);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshKey]);

  return (
    <select className="select" value={value || ""} onChange={(e) => onChange(e.target.value)}>
      {runs.length === 0 ? <option value="">No runs yet</option> : null}
      {runs.map((r) => (
        <option key={r.run_id} value={r.run_id}>
          {(r.user_input || "(empty)").slice(0, 40)} · {r.status}
        </option>
      ))}
    </select>
  );
}
