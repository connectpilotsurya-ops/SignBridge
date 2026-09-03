"use client";

import { useMemo, useState } from "react";
import type { CapabilityGraph as CapabilityGraphType } from "@/types/api";

const KIND_STYLES: Record<string, { bg: string; border: string; text: string; label: string }> = {
  candidate: { bg: "#5D5FEF", border: "#4B4ACF", text: "#FFFFFF", label: "Candidate" },
  requirement: { bg: "#EEF2FF", border: "#6366F1", text: "#4338CA", label: "Requirement" },
  skill: { bg: "#F0FDF4", border: "#10B981", text: "#15803D", label: "Evidenced Skill" },
  experience: { bg: "#FEF3C7", border: "#F59E0B", text: "#B45309", label: "Experience" },
  project: { bg: "#ECFDF5", border: "#059669", text: "#047857", label: "Project" },
  achievement: { bg: "#F0F9FF", border: "#0284C7", text: "#0369A1", label: "Achievement" },
  evidence: { bg: "#F8FAFC", border: "#94A3B8", text: "#475569", label: "Evidence Run" },
};

function getStyle(kind: string) {
  return KIND_STYLES[kind] ?? { bg: "#F8FAFC", border: "#94A3B8", text: "#334155", label: kind };
}

export function CapabilityGraph({ graph }: { graph: CapabilityGraphType }) {
  const [hovered, setHovered] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // SVG canvas dimensions
  const width = 760;
  const height = 520;
  const centerX = width / 2;
  const centerY = height / 2;

  const centerNode = useMemo(
    () => graph.nodes.find((n) => n.kind === "candidate") ?? graph.nodes[0],
    [graph.nodes]
  );

  // Hierarchical Concentric Layout:
  // Core (r=0): Candidate
  // Ring 1 (r=155): Job Requirements
  // Ring 2 (r=265): Evidenced Claims, Skills, Achievements
  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number; tier: number }>();
    if (!centerNode) return map;

    map.set(centerNode.id, { x: centerX, y: centerY, tier: 0 });

    const requirements = graph.nodes.filter(
      (n) => n.id !== centerNode.id && (n.kind === "requirement" || n.kind === "job")
    );
    const outerNodes = graph.nodes.filter(
      (n) => n.id !== centerNode.id && n.kind !== "requirement" && n.kind !== "job"
    );

    // Ring 1: Requirements
    const r1Radius = 155;
    const reqCount = Math.max(requirements.length, 1);
    requirements.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / reqCount - Math.PI / 2;
      map.set(node.id, {
        x: centerX + r1Radius * Math.cos(angle),
        y: centerY + r1Radius * Math.sin(angle),
        tier: 1,
      });
    });

    // Ring 2: Outer claims & skills
    const r2Radius = 265;
    const outerCount = Math.max(outerNodes.length, 1);
    outerNodes.forEach((node, i) => {
      const angle = (2 * Math.PI * i) / outerCount - Math.PI / 2 + Math.PI / outerCount;
      map.set(node.id, {
        x: centerX + r2Radius * Math.cos(angle),
        y: centerY + r2Radius * Math.sin(angle),
        tier: 2,
      });
    });

    return map;
  }, [graph.nodes, centerNode, centerX, centerY]);

  // Connected node IDs map for hover highlighting
  const connectedNodeIds = useMemo(() => {
    if (!hovered) return new Set<string>();
    const set = new Set<string>([hovered]);
    graph.edges.forEach((edge) => {
      if (edge.source === hovered) set.add(edge.target);
      if (edge.target === hovered) set.add(edge.source);
    });
    return set;
  }, [hovered, graph.edges]);

  if (graph.nodes.length === 0) {
    return (
      <div className="p-8 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-sm text-ink-400">
        No capability graph data available for this candidate.
      </div>
    );
  }

  const activeNodeDetail = graph.nodes.find((n) => n.id === (selectedNode || hovered));

  return (
    <div className="relative bg-gradient-to-b from-slate-900/5 via-white to-indigo-50/20 rounded-2xl border border-border/80 p-4 shadow-sm select-none">
      {/* Visual Header & Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4 px-2">
        <div>
          <h3 className="font-display font-bold text-sm text-ink-900 flex items-center gap-2">
            <span>🌐</span> Tiered Evidence & Capability Graph
          </h3>
          <p className="text-xs text-ink-500">
            Concentric mapping: Candidate (Core) → Job Requirements (Inner Ring) → Evidenced Claims (Outer Ring)
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2 text-[11px] font-medium pointer-events-none">
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-primary/10 text-primary border border-primary/20">
            <span className="w-2 h-2 rounded-full bg-primary" /> Candidate
          </span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700 border border-indigo-200">
            <span className="w-2 h-2 rounded-full bg-indigo-500" /> Requirement
          </span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200">
            <span className="w-2 h-2 rounded-full bg-emerald-500" /> Evidenced Skill
          </span>
          <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-amber-50 text-amber-700 border border-amber-200">
            <span className="w-2 h-2 rounded-full bg-amber-500" /> Experience
          </span>
        </div>
      </div>

      {/* Main SVG Graph Canvas */}
      <div className="overflow-x-auto scrollbar-thin flex justify-center py-2">
        <svg viewBox={`0 0 ${width} ${height}`} className="w-full max-w-[760px] h-auto pointer-events-auto">
          <defs>
            {/* Soft backdrop radial gradients for concentric rings */}
            <radialGradient id="ring-bg" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="#5D5FEF" stopOpacity="0.05" />
              <stop offset="60%" stopColor="#6366F1" stopOpacity="0.02" />
              <stop offset="100%" stopColor="#FAFBFD" stopOpacity="0" />
            </radialGradient>
          </defs>

          {/* Concentric Guide Circles — pointer-events-none to prevent event interference */}
          <circle cx={centerX} cy={centerY} r={265} fill="url(#ring-bg)" stroke="#E2E8F0" strokeWidth="1" strokeDasharray="4 4" className="pointer-events-none" />
          <circle cx={centerX} cy={centerY} r={155} fill="none" stroke="#C7D2FE" strokeWidth="1.5" strokeDasharray="6 4" opacity="0.6" className="pointer-events-none" />

          {/* Graph Edges — pointer-events-none to prevent mouse flickering */}
          {graph.edges.map((edge, i) => {
            const from = positions.get(edge.source);
            const to = positions.get(edge.target);
            if (!from || !to) return null;

            const isHighlighted =
              hovered && (edge.source === hovered || edge.target === hovered);
            const isDimmed = hovered && !isHighlighted;

            return (
              <g key={i} opacity={isDimmed ? 0.15 : isHighlighted ? 1 : 0.65} className="pointer-events-none transition-opacity duration-150">
                <line
                  x1={from.x}
                  y1={from.y}
                  x2={to.x}
                  y2={to.y}
                  stroke={isHighlighted ? "#5D5FEF" : "#CBD5E1"}
                  strokeWidth={isHighlighted ? 2.5 : 1.5}
                />
                {edge.relationship && (
                  <g transform={`translate(${(from.x + to.x) / 2}, ${(from.y + to.y) / 2})`}>
                    <rect
                      x={-35}
                      y={-9}
                      width={70}
                      height={18}
                      rx={9}
                      fill="#FFFFFF"
                      stroke={isHighlighted ? "#5D5FEF" : "#E2E8F0"}
                      strokeWidth={1}
                    />
                    <text
                      x={0}
                      y={3}
                      fontSize={9}
                      fontWeight={600}
                      fill={isHighlighted ? "#5D5FEF" : "#64748B"}
                      textAnchor="middle"
                    >
                      {edge.relationship}
                    </text>
                  </g>
                )}
              </g>
            );
          })}

          {/* Graph Nodes */}
          {graph.nodes.map((node) => {
            const pos = positions.get(node.id);
            if (!pos) return null;

            const isCenter = node.id === centerNode?.id;
            const style = getStyle(node.kind);

            const isHovered = hovered === node.id;
            const isConnected = connectedNodeIds.has(node.id);
            const isDimmed = hovered && !isConnected;

            // Pill dimensions
            const labelText = node.label.length > 20 ? node.label.slice(0, 19) + "…" : node.label;
            const pillWidth = isCenter ? 140 : Math.max(labelText.length * 7.2 + 28, 90);
            const pillHeight = isCenter ? 36 : 28;

            return (
              <g
                key={node.id}
                transform={`translate(${pos.x}, ${pos.y})`}
                opacity={isDimmed ? 0.25 : 1}
                onMouseEnter={() => setHovered(node.id)}
                onMouseLeave={() => setHovered(null)}
                onClick={() => setSelectedNode(node.id === selectedNode ? null : node.id)}
                className="cursor-pointer"
              >
                {/* Stable Buffer Target to prevent mouseout jitter */}
                <rect
                  x={-pillWidth / 2 - 6}
                  y={-pillHeight / 2 - 6}
                  width={pillWidth + 12}
                  height={pillHeight + 12}
                  fill="transparent"
                  pointerEvents="all"
                />

                {/* Node Pill Shape */}
                <rect
                  x={-pillWidth / 2}
                  y={-pillHeight / 2}
                  width={pillWidth}
                  height={pillHeight}
                  rx={pillHeight / 2}
                  fill={isCenter ? "#5D5FEF" : isHovered ? "#FFFFFF" : style.bg}
                  stroke={isHovered ? "#4338CA" : isCenter ? "#4B4ACF" : style.border}
                  strokeWidth={isHovered ? 3 : isCenter ? 2.5 : 1.5}
                  pointerEvents="none"
                />

                {/* Node Status Dot */}
                {!isCenter && (
                  <circle
                    cx={-pillWidth / 2 + 12}
                    cy={0}
                    r={4}
                    fill={node.status === "missing" ? "#EF4444" : style.border}
                    pointerEvents="none"
                  />
                )}

                {/* Node Label Text */}
                <text
                  x={isCenter ? 0 : 4}
                  y={4}
                  fontSize={isCenter ? 12 : 11}
                  fontWeight={isCenter ? 800 : isHovered ? 700 : 600}
                  fill={isCenter ? "#FFFFFF" : isHovered ? "#4338CA" : style.text}
                  textAnchor="middle"
                  pointerEvents="none"
                >
                  {labelText}
                </text>
              </g>
            );
          })}
        </svg>
      </div>

      {/* Dynamic Node Context Details Panel */}
      {activeNodeDetail && (
        <div className="mt-3 p-3.5 rounded-xl bg-white border border-primary/30 shadow-sm flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <span className="font-bold text-ink-900">{activeNodeDetail.label}</span>
              <span className="px-2 py-0.5 rounded-md text-[10px] uppercase font-bold tracking-wider" style={{ backgroundColor: getStyle(activeNodeDetail.kind).bg, color: getStyle(activeNodeDetail.kind).text }}>
                {activeNodeDetail.kind}
              </span>
            </div>
            {activeNodeDetail.status && (
              <p className="text-ink-500 text-[11px]">
                Status: <span className="font-semibold text-ink-700">{activeNodeDetail.status.replace("_", " ")}</span>
              </p>
            )}
          </div>
          <div className="text-right text-[11px] text-ink-400 font-medium">
            Hover or click node to inspect
          </div>
        </div>
      )}
    </div>
  );
}
