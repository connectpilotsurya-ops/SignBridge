"use client";

import { useMemo } from "react";
import type { RankedCandidate } from "@/types/api";

interface MetricDimension {
  key: string;
  label: string;
  getValue: (c: RankedCandidate) => number;
}

const METRICS: MetricDimension[] = [
  { key: "must_have", label: "Must-Have Coverage", getValue: (c) => c.must_have_coverage },
  { key: "evidence_confidence", label: "Evidence Confidence", getValue: (c) => c.evidence_confidence },
  { key: "document_integrity", label: "Document Integrity", getValue: (c) => c.document_integrity },
  { key: "match_score", label: "Match Score", getValue: (c) => c.match_score },
  { key: "transferability", label: "Transferable Signal", getValue: (c) => c.transferability },
];

const COLORS = ["#5D5FEF", "#10B981", "#F59E0B", "#EC4899", "#8B5CF6"];

export function RadarChart({
  candidates,
  size = 320,
}: {
  candidates: RankedCandidate[];
  size?: number;
}) {
  const center = size / 2;
  const radius = size / 2 - 50;
  const angleStep = (2 * Math.PI) / METRICS.length;

  const candidatePolygons = useMemo(() => {
    return candidates.map((candidate, idx) => {
      const points = METRICS.map((metric, i) => {
        const val = Math.min(Math.max(metric.getValue(candidate), 0), 100);
        const r = (val / 100) * radius;
        const angle = i * angleStep - Math.PI / 2;
        const x = center + r * Math.cos(angle);
        const y = center + r * Math.sin(angle);
        return { x, y, val };
      });

      const polygonStr = points.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(" ");
      const color = COLORS[idx % COLORS.length];

      return { candidate, points, polygonStr, color };
    });
  }, [candidates, radius, center, angleStep]);

  if (candidates.length === 0) return null;

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size} className="overflow-visible select-none">
        {/* Background Concentric Radar Grid Circles */}
        {[0.2, 0.4, 0.6, 0.8, 1.0].map((step, idx) => (
          <polygon
            key={idx}
            points={METRICS.map((_, i) => {
              const r = step * radius;
              const angle = i * angleStep - Math.PI / 2;
              const x = center + r * Math.cos(angle);
              const y = center + r * Math.sin(angle);
              return `${x.toFixed(1)},${y.toFixed(1)}`;
            }).join(" ")}
            fill={idx === 4 ? "rgba(93, 95, 239, 0.02)" : "none"}
            stroke="#E2E8F0"
            strokeWidth="1"
            strokeDasharray={idx < 4 ? "3 3" : "none"}
          />
        ))}

        {/* Axis Lines & Labels */}
        {METRICS.map((metric, i) => {
          const angle = i * angleStep - Math.PI / 2;
          const x = center + radius * Math.cos(angle);
          const y = center + radius * Math.sin(angle);

          const labelX = center + (radius + 24) * Math.cos(angle);
          const labelY = center + (radius + 18) * Math.sin(angle);

          return (
            <g key={metric.key}>
              <line x1={center} y1={center} x2={x} y2={y} stroke="#CBD5E1" strokeWidth="1" />
              <text
                x={labelX}
                y={labelY}
                fontSize={10}
                fontWeight={600}
                fill="#475569"
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {metric.label}
              </text>
            </g>
          );
        })}

        {/* Candidate Fit Polygons */}
        {candidatePolygons.map(({ candidate, polygonStr, points, color }) => (
          <g key={candidate.application_id}>
            <polygon
              points={polygonStr}
              fill={color}
              fillOpacity={candidates.length === 1 ? 0.25 : 0.15}
              stroke={color}
              strokeWidth={candidates.length === 1 ? 2.5 : 2}
              className="transition-all duration-300 hover:fill-opacity-30"
            />
            {points.map((p, i) => (
              <circle key={i} cx={p.x} cy={p.y} r={4} fill="#FFFFFF" stroke={color} strokeWidth={2} />
            ))}
          </g>
        ))}
      </svg>

      {/* Legend */}
      <div className="flex flex-wrap gap-3 justify-center mt-4">
        {candidatePolygons.map(({ candidate, color }) => (
          <div key={candidate.application_id} className="flex items-center gap-1.5 text-xs font-semibold text-ink-700">
            <span className="w-3 h-3 rounded-full border-2" style={{ backgroundColor: color, borderColor: color }} />
            <span>#{candidate.rank} {candidate.display_label} ({candidate.match_score.toFixed(0)} pts)</span>
          </div>
        ))}
      </div>
    </div>
  );
}
