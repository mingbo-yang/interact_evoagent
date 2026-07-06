"use client";

import { useMemo } from "react";
import ReactFlow, { Background, BackgroundVariant, Controls, MiniMap } from "reactflow";
import "reactflow/dist/style.css";

import FlowNode from "./FlowNode";
import type { WorkflowEvent } from "@/lib/event-client";
import { buildFlow } from "@/lib/flow-layout";

const nodeTypes = { fnode: FlowNode };

type Props = {
  events: WorkflowEvent[];
  running: boolean;
};

export default function FlowGraph({ events, running }: Props) {
  const { nodes, edges } = useMemo(() => buildFlow(events, running), [events, running]);

  return (
    <div className="flow-wrap">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.25 }}
        proOptions={{ hideAttribution: true }}
        minZoom={0.3}
        maxZoom={1.6}
        nodesDraggable={false}
        nodesConnectable={false}
      >
        <Background variant={BackgroundVariant.Dots} gap={22} size={1} color="#22304d" />
        <MiniMap
          pannable
          zoomable
          style={{ background: "#0f1626", border: "1px solid #24304a", borderRadius: 8 }}
          nodeColor={() => "#2a3654"}
          maskColor="rgba(11,15,26,0.6)"
        />
        <Controls showInteractive={false} />
      </ReactFlow>
      <div className="flow-legend">
        <div className="lg"><span className="sw" style={{ background: "#60a5fa" }} /> running</div>
        <div className="lg"><span className="sw" style={{ background: "#34d399" }} /> success</div>
        <div className="lg"><span className="sw" style={{ background: "#f87171" }} /> failed</div>
        <div className="lg"><span className="sw" style={{ background: "#fbbf24" }} /> paused</div>
      </div>
    </div>
  );
}
