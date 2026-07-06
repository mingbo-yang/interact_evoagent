"use client";

import { useEffect, useState } from "react";

import BarList, { type BarItem } from "@/components/charts/BarList";
import Donut from "@/components/charts/Donut";
import LineChart from "@/components/charts/LineChart";
import TopNav from "@/components/TopNav";
import {
  getNodeMetrics,
  getStats,
  getTimeline,
  getToolMetrics,
  type NodeMetric,
  type Stats,
  type TimelinePoint,
  type ToolMetric
} from "@/lib/api-client";
import { fmtDuration } from "@/lib/ui";

export default function MetricsPage() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [nodes, setNodes] = useState<NodeMetric[]>([]);
  const [tools, setTools] = useState<ToolMetric[]>([]);
  const [timeline, setTimeline] = useState<TimelinePoint[]>([]);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const load = () =>
      Promise.all([getStats(), getNodeMetrics(), getToolMetrics(), getTimeline(20)])
        .then(([s, n, t, tl]) => {
          if (cancelled) return;
          setStats(s);
          setNodes(n.nodes);
          setTools(t.tools);
          setTimeline(tl.timeline);
        })
        .catch(() => undefined);
    load();
    const id = setInterval(() => setTick((x) => x + 1), 4000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [tick]);

  const successRate = stats && stats.total_runs > 0 ? stats.completed / stats.total_runs : 0;
  const toolSuccess =
    tools.reduce((a, t) => a + t.success, 0) /
    Math.max(1, tools.reduce((a, t) => a + t.total, 0));

  const nodeBars: BarItem[] = nodes.map((n) => ({
    label: n.node_type,
    value: n.avg_ms,
    display: fmtDuration(n.avg_ms)
  }));
  const toolBars: BarItem[] = tools.map((t) => ({
    label: t.tool,
    value: t.total,
    display: `${t.total} · ${Math.round(t.success_rate * 100)}%`
  }));
  const durationSeries = timeline.map((t) => ({ value: t.duration_ms, status: t.status }));

  return (
    <div className="page-shell">
      <header className="header">
        <TopNav />
        <div className="header-spacer" />
        <span className="meta" style={{ color: "var(--text-faint)", fontSize: 12 }}>
          auto-refresh · 4s
        </span>
      </header>
      <div className="page-content" style={{ overflow: "auto" }}>
        <div className="metrics-grid">
          <div className="mcard">
            <span className="m-title">🏃 Total runs</span>
            <span className="m-big">{stats?.total_runs ?? 0}</span>
            <span className="m-sub">{stats?.completed ?? 0} completed · {stats?.failed ?? 0} failed</span>
          </div>
          <div className="mcard">
            <span className="m-title">🔧 Tool calls</span>
            <span className="m-big">{stats?.total_tools ?? 0}</span>
            <span className="m-sub">{tools.length} distinct tools</span>
          </div>
          <div className="mcard">
            <span className="m-title">💾 Memories</span>
            <span className="m-big">{stats?.total_memories ?? 0}</span>
            <span className="m-sub">{stats?.total_artifacts ?? 0} artifacts</span>
          </div>
          <div className="mcard">
            <span className="m-title">⏱️ Avg duration</span>
            <span className="m-big">{fmtDuration(stats?.avg_duration_ms)}</span>
            <span className="m-sub">{stats?.total_events ?? 0} events total</span>
          </div>

          <div className="mcard span2" style={{ alignItems: "center", flexDirection: "row", gap: 20 }}>
            <Donut value={successRate} sub="run success" />
            <div style={{ flex: 1 }}>
              <span className="m-title">✅ Run success rate</span>
              <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-dim)" }}>
                {stats?.completed ?? 0} / {stats?.total_runs ?? 0} runs completed successfully.
              </div>
            </div>
          </div>

          <div className="mcard span2" style={{ alignItems: "center", flexDirection: "row", gap: 20 }}>
            <Donut value={toolSuccess} sub="tool success" />
            <div style={{ flex: 1 }}>
              <span className="m-title">🔧 Tool success rate</span>
              <div style={{ marginTop: 8, fontSize: 13, color: "var(--text-dim)" }}>
                {tools.reduce((a, t) => a + t.success, 0)} / {tools.reduce((a, t) => a + t.total, 0)} tool calls succeeded.
              </div>
            </div>
          </div>

          <div className="mcard span2">
            <span className="m-title">🧠 Avg duration by node</span>
            <BarList items={nodeBars} />
          </div>
          <div className="mcard span2">
            <span className="m-title">🛠️ Tool usage (count · success%)</span>
            <BarList items={toolBars} />
          </div>

          <div className="mcard span4">
            <span className="m-title">📈 Run duration trend (recent {timeline.length})</span>
            <LineChart points={durationSeries} unit="ms" />
          </div>
        </div>
      </div>
    </div>
  );
}
