"use client";

import FlowGraph from "@/components/FlowGraph";
import RunSelector from "@/components/RunSelector";
import TopNav from "@/components/TopNav";
import { useAppState } from "@/lib/app-state";

export default function FlowPage() {
  const app = useAppState();

  return (
    <div className="page-shell">
      <header className="header">
        <TopNav />
        <div className="header-spacer" />
        <span className="meta" style={{ color: "var(--text-faint)", fontSize: 12 }}>
          workflow as flowchart{app.running ? " · live" : ""}
        </span>
        <RunSelector value={app.currentRunId} onChange={app.openRun} refreshKey={app.historyKey} />
      </header>
      <div className="page-content">
        {app.currentRunId ? (
          <FlowGraph events={app.events} running={app.running} />
        ) : (
          <div className="flow-wrap">
            <div className="empty" style={{ paddingTop: 120 }}>
              在控制台发起一个任务，或从右上角选择一个运行，即可查看其工作流流程图。
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
