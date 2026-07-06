"use client";

import { Handle, Position, type NodeProps } from "reactflow";

type FNodeData = {
  icon: string;
  name: string;
  sub: string;
  status: string;
};

export default function FlowNode({ data }: NodeProps<FNodeData>) {
  return (
    <div className={`fnode st-${data.status}`}>
      <Handle type="target" position={Position.Left} style={{ background: "#3a4a70", border: "none" }} />
      <div className="fn-head">
        <span className="fn-ico">{data.icon}</span>
        <span style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{data.name}</span>
      </div>
      <div className="fn-sub">{data.sub}</div>
      <Handle type="source" position={Position.Right} style={{ background: "#3a4a70", border: "none" }} />
    </div>
  );
}
