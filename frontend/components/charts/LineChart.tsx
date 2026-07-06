"use client";

export type SeriesPoint = { value: number; status?: string };

type Props = {
  points: SeriesPoint[];
  height?: number;
  unit?: string;
};

// A responsive area/line chart with status-colored dots.
export default function LineChart({ points, height = 120, unit }: Props) {
  if (points.length === 0) {
    return <div className="empty" style={{ padding: 20 }}>暂无数据</div>;
  }
  const W = 100; // viewBox width (percentage-like, scales via preserveAspectRatio none)
  const H = height;
  const max = Math.max(1, ...points.map((p) => p.value));
  const n = points.length;
  const step = n > 1 ? W / (n - 1) : W;
  const coords = points.map((p, i) => {
    const x = n > 1 ? i * step : W / 2;
    const y = H - (p.value / max) * (H - 16) - 8;
    return { x, y, p };
  });
  const line = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");
  const area = `${line} L ${coords[coords.length - 1].x} ${H} L ${coords[0].x} ${H} Z`;

  const dotColor = (s?: string) =>
    s === "failed" ? "#f87171" : s === "completed" ? "#34d399" : s === "running" ? "#60a5fa" : "#8b5cf6";

  return (
    <div style={{ width: "100%" }}>
      <svg width="100%" height={H} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
        <defs>
          <linearGradient id="areaGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(109,139,255,0.35)" />
            <stop offset="100%" stopColor="rgba(109,139,255,0)" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#areaGrad)" />
        <path d={line} fill="none" stroke="#6d8bff" strokeWidth={1.5} vectorEffect="non-scaling-stroke" />
      </svg>
      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 4 }}>
        {coords.map((c, i) => (
          <span
            key={i}
            title={`${points[i].value}${unit ?? ""} · ${points[i].status ?? ""}`}
            style={{ width: 8, height: 8, borderRadius: "50%", background: dotColor(points[i].status) }}
          />
        ))}
      </div>
    </div>
  );
}
