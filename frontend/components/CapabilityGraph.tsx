"use client";

import { useMemo, useState } from "react";
import type { CapabilityGraph as CapabilityGraphType } from "@/types/api";

const KIND_COLORS: Record<string, string> = {
  candidate: "#0F172A",
  job: "#64748B",
  requirement: "#5D5FEF",
  skill: "#6366F1",
  experience: "#10B981",
  project: "#10B981",
  achievement: "#10B981",
  certification: "#10B981",
  evidence: "#64748B",
};

const STATUS_DASH: Record<string, string> = {
  missing: "4 3",
  requires_verification: "2 2",
};

function colorFor(kind: string): string {
  return KIND_COLORS[kind] ?? "#64748B";
}

export function CapabilityGraph({ graph }: { graph: CapabilityGraphType }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const size = 460;
  const center = size / 2;

  const centerNodeId = graph.nodes.find((n) => n.kind === "candidate")?.id ?? graph.nodes[0]?.id;

  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>();
    const ringNodes = graph.nodes.filter((n) => n.id !== centerNodeId);
    if (centerNodeId) map.set(centerNodeId, { x: center, y: center });
    const n = Math.max(ringNodes.length, 1);
    ringNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / n - Math.PI / 2;
      const radius = size / 2 - 70;
      map.set(node.id, {
        x: center + radius * Math.cos(angle),
        y: center + radius * Math.sin(angle),
      });
    });
    return map;
  }, [graph.nodes, centerNodeId, center, size]);

  if (graph.nodes.length === 0) {
    return <p className="text-sm text-ink-400">No graph data available for this candidate.</p>;
  }

  return (
    <div className="overflow-x-auto scrollbar-thin">
      <svg width={size} height={size} className="mx-auto">
        {graph.edges.map((edge, i) => {
          const from = positions.get(edge.source);
          const to = positions.get(edge.target);
          if (!from || !to) return null;
          const dimmed = hovered && hovered !== edge.source && hovered !== edge.target;
          return (
            <g key={i} opacity={dimmed ? 0.12 : 1}>
              <line x1={from.x} y1={from.y} x2={to.x} y2={to.y} stroke="#CBD5E1" strokeWidth={1.5} />
              <text
                x={(from.x + to.x) / 2}
                y={(from.y + to.y) / 2}
                fontSize={9}
                fill="#64748B"
                textAnchor="middle"
                className="select-none font-medium"
              >
                {edge.relationship}
              </text>
            </g>
          );
        })}
        {graph.nodes.map((node) => {
          const pos = positions.get(node.id);
          if (!pos) return null;
          const isCenter = node.id === centerNodeId;
          const dimmed = hovered && hovered !== node.id;
          const dash = node.status ? STATUS_DASH[node.status] : undefined;
          return (
            <g
              key={node.id}
              opacity={dimmed ? 0.25 : 1}
              onMouseEnter={() => setHovered(node.id)}
              onMouseLeave={() => setHovered(null)}
              className="cursor-default"
            >
              <circle
                cx={pos.x}
                cy={pos.y}
                r={isCenter ? 26 : 17}
                fill={isCenter ? colorFor(node.kind) : "#FFFFFF"}
                stroke={colorFor(node.kind)}
                strokeWidth={2}
                strokeDasharray={dash}
              />
              <text
                x={pos.x}
                y={pos.y + (isCenter ? 42 : 32)}
                fontSize={11}
                fontWeight={600}
                fill="#0F172A"
                textAnchor="middle"
                className="select-none"
              >
                {node.label.length > 18 ? node.label.slice(0, 17) + "…" : node.label}
              </text>
            </g>
          );
        })}
      </svg>
      <div className="flex flex-wrap gap-3 justify-center mt-2">
        {["candidate", "requirement", "skill", "experience", "evidence"].map((kind) => (
          <div key={kind} className="flex items-center gap-1.5 text-xs text-ink-500 font-medium">
            <span className="h-2.5 w-2.5 rounded-full border-2" style={{ borderColor: colorFor(kind), backgroundColor: kind === "candidate" ? colorFor(kind) : "#FFFFFF" }} />
            {kind}
          </div>
        ))}
      </div>
    </div>
  );
}
