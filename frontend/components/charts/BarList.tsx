"use client";

export type BarItem = { label: string; value: number; display?: string };

type Props = {
  items: BarItem[];
  unit?: string;
  color?: string;
};

export default function BarList({ items, unit, color }: Props) {
  const max = Math.max(1, ...items.map((i) => i.value));
  if (items.length === 0) {
    return <div className="empty" style={{ padding: 20 }}>暂无数据</div>;
  }
  return (
    <div style={{ marginTop: 6 }}>
      {items.map((it) => {
        // Normalize against the max; give any non-zero value a small floor width
        // so short bars stay visible next to a dominant one.
        const pct = it.value > 0 ? Math.max(4, (it.value / max) * 100) : 0;
        return (
          <div key={it.label} className="bar-row">
            <span className="k" title={it.label}>{it.label}</span>
            <span className="bar-track">
              <span
                className="bar-fill"
                style={{ width: `${pct}%`, background: color ?? undefined }}
              />
            </span>
            <span className="val">{it.display ?? `${it.value}${unit ?? ""}`}</span>
          </div>
        );
      })}
    </div>
  );
}
