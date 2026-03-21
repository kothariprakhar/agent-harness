"use client";

import { useMemo } from "react";
import ReactFlow, {
  Background,
  Controls,
  Node,
  Edge,
  Position,
} from "reactflow";
import "reactflow/dist/style.css";
import { AGENT_COLORS, AGENT_LABELS } from "@/lib/constants";
import type { PipelineEvent } from "@/lib/types";

interface Props {
  events: PipelineEvent[];
}

function getAgentStatus(
  agentName: string,
  events: PipelineEvent[]
): "idle" | "working" | "completed" | "failed" {
  const agentEvents = events.filter(
    (e) => e.data?.agent_name === agentName || e.data?.message?.toLowerCase().includes(agentName)
  );
  if (agentEvents.length === 0) return "idle";

  const lastEvent = agentEvents[agentEvents.length - 1];
  const type = lastEvent.type;
  if (type === "pipeline_complete" || type === "message_received") return "completed";
  if (type === "pipeline_error") return "failed";
  return "working";
}

const statusBorderStyles: Record<string, string> = {
  idle: "border-gray-600",
  working: "border-yellow-400 animate-pulse",
  completed: "border-green-500",
  failed: "border-red-500",
};

export default function PipelineDAG({ events }: Props) {
  const nodes: Node[] = useMemo(
    () => [
      {
        id: "orchestrator",
        position: { x: 300, y: 20 },
        data: { label: "Orchestrator" },
        style: {
          background: "#1e1e1e",
          color: "white",
          border: `2px solid ${AGENT_COLORS.orchestrator}`,
          borderRadius: 12,
          padding: "10px 20px",
          fontWeight: 600,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      },
      {
        id: "researcher",
        position: { x: 50, y: 150 },
        data: { label: "Researcher" },
        style: {
          background: "#1e1e1e",
          color: "white",
          border: `2px solid ${AGENT_COLORS.researcher}`,
          borderRadius: 12,
          padding: "10px 20px",
          fontWeight: 600,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      },
      {
        id: "data_analyst",
        position: { x: 250, y: 150 },
        data: { label: "Data Analyst" },
        style: {
          background: "#1e1e1e",
          color: "white",
          border: `2px solid ${AGENT_COLORS.data_analyst}`,
          borderRadius: 12,
          padding: "10px 20px",
          fontWeight: 600,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      },
      {
        id: "writer",
        position: { x: 450, y: 150 },
        data: { label: "Writer" },
        style: {
          background: "#1e1e1e",
          color: "white",
          border: `2px solid ${AGENT_COLORS.writer}`,
          borderRadius: 12,
          padding: "10px 20px",
          fontWeight: 600,
        },
        sourcePosition: Position.Bottom,
        targetPosition: Position.Top,
      },
      {
        id: "critic",
        position: { x: 350, y: 280 },
        data: { label: "Critic" },
        style: {
          background: "#1e1e1e",
          color: "white",
          border: `2px solid ${AGENT_COLORS.critic}`,
          borderRadius: 12,
          padding: "10px 20px",
          fontWeight: 600,
        },
        sourcePosition: Position.Top,
        targetPosition: Position.Top,
      },
    ],
    []
  );

  const edges: Edge[] = useMemo(
    () => [
      { id: "e-orch-res", source: "orchestrator", target: "researcher", animated: true, style: { stroke: AGENT_COLORS.researcher } },
      { id: "e-orch-da", source: "orchestrator", target: "data_analyst", animated: true, style: { stroke: AGENT_COLORS.data_analyst } },
      { id: "e-orch-writer", source: "orchestrator", target: "writer", animated: true, style: { stroke: AGENT_COLORS.writer } },
      { id: "e-writer-critic", source: "writer", target: "critic", animated: true, style: { stroke: AGENT_COLORS.critic } },
      {
        id: "e-critic-writer",
        source: "critic",
        target: "writer",
        animated: true,
        style: { stroke: AGENT_COLORS.critic, strokeDasharray: "5,5" },
        label: "Feedback Loop",
        labelStyle: { fill: "#a0a0a0", fontSize: 10 },
      },
    ],
    []
  );

  return (
    <div className="h-[350px] bg-[#141414] rounded-lg border border-[#333]">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
      >
        <Background color="#333" gap={20} />
        <Controls showInteractive={false} />
      </ReactFlow>
    </div>
  );
}
