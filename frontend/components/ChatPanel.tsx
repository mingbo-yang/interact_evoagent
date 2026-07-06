"use client";

import { useEffect, useRef } from "react";
import { MessageInput } from "@chatscope/chat-ui-kit-react";
import ReactMarkdown from "react-markdown";

export type ChatMessage = {
  role: "user" | "assistant";
  content: string;
};

type Props = {
  messages: ChatMessage[];
  disabled: boolean;
  onSend: (text: string) => void;
  approvalPending?: boolean;
  approvalText?: string;
  onApprove?: (approved: boolean) => void;
};

export default function ChatPanel({
  messages,
  disabled,
  onSend,
  approvalPending,
  approvalText,
  onApprove
}: Props) {
  const endRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, approvalPending]);

  return (
    <div className="panel chat-cell" style={{ height: "100%" }}>
      <div className="panel-head">
        <span className="icon">💬</span> Conversation
        <span className="count">{messages.length} messages</span>
      </div>
      <div className="panel-body" style={{ padding: "10px 4px" }}>
        {messages.map((m, idx) => (
          <div
            key={`${m.role}-${idx}`}
            style={{
              display: "flex",
              justifyContent: m.role === "user" ? "flex-end" : "flex-start",
              padding: "6px 14px"
            }}
          >
            <div
              className="md"
              style={{
                maxWidth: "80%",
                padding: "10px 14px",
                borderRadius: 14,
                fontSize: 13.5,
                lineHeight: 1.55,
                background:
                  m.role === "user"
                    ? "linear-gradient(135deg, rgba(109,139,255,0.26), rgba(139,92,246,0.26))"
                    : "var(--bg-2)",
                border: "1px solid var(--border-soft)"
              }}
            >
              <ReactMarkdown>{m.content}</ReactMarkdown>
            </div>
          </div>
        ))}

        {approvalPending && onApprove ? (
          <div style={{ display: "flex", justifyContent: "flex-start", padding: "6px 14px" }}>
            <div className="approval-card">
              <div className="ac-head">
                <span className="ac-ico">⏸️</span>
                <span>需要你的审批</span>
              </div>
              <div className="ac-body">{approvalText || "检测到高风险操作，是否允许执行？"}</div>
              <div className="ac-actions">
                <button className="btn success" onClick={() => onApprove(true)}>✓ 允许 (yes)</button>
                <button className="btn danger" onClick={() => onApprove(false)}>✕ 拒绝 (no)</button>
              </div>
            </div>
          </div>
        ) : null}

        <div ref={endRef} />
      </div>
      <div style={{ borderTop: "1px solid var(--border-soft)" }}>
        <MessageInput
          placeholder={disabled ? "Run in progress…" : "输入任务并回车 (Shift+Enter 换行)"}
          attachButton={false}
          disabled={disabled}
          onSend={(_inner, text) => onSend(text)}
        />
      </div>
    </div>
  );
}
