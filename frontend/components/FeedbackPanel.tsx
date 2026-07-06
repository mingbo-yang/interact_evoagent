"use client";

import { useState } from "react";

type Props = {
  runId: string | null;
  disabled: boolean;
  onSubmit: (score: number, comment: string) => Promise<void>;
};

export default function FeedbackPanel({ runId, disabled, onSubmit }: Props) {
  const [score, setScore] = useState(5);
  const [comment, setComment] = useState("");
  const [saved, setSaved] = useState(false);

  const handleSubmit = async () => {
    if (!runId) return;
    await onSubmit(score, comment);
    setSaved(true);
    setComment("");
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div style={{ padding: 14, display: "flex", flexDirection: "column", gap: 10 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <span style={{ fontSize: 12, color: "var(--text-faint)" }}>Rating</span>
        {[1, 2, 3, 4, 5].map((s) => (
          <span
            key={s}
            onClick={() => !disabled && runId && setScore(s)}
            style={{
              cursor: disabled || !runId ? "not-allowed" : "pointer",
              fontSize: 20,
              opacity: s <= score ? 1 : 0.3,
              transition: "opacity 0.15s"
            }}
          >
            ⭐
          </span>
        ))}
      </div>
      <textarea
        value={comment}
        placeholder="Optional feedback or correction…"
        onChange={(e) => setComment(e.target.value)}
        disabled={disabled || !runId}
        rows={3}
        style={{
          resize: "vertical",
          background: "var(--bg-1)",
          color: "var(--text)",
          border: "1px solid var(--border)",
          borderRadius: 8,
          padding: 8,
          fontSize: 13
        }}
      />
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button className="btn primary" onClick={handleSubmit} disabled={disabled || !runId}>
          Submit feedback
        </button>
        {saved ? <span style={{ color: "var(--success)", fontSize: 12 }}>Saved ✓</span> : null}
      </div>
    </div>
  );
}
