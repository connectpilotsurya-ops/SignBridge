"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { JobRankingResponse, RankedCandidate, SelectionStatus } from "@/types/api";
import {
  Button,
  Card,
  EmptyState,
  PageHeader,
  RankingStatusBadge,
  SelectionStatusBadge,
  Spinner,
} from "@/components/ui";

function fmt(n: number | null | undefined, digits = 0): string {
  if (n === null || n === undefined) return "—";
  return n.toFixed(digits);
}

// Spec update §17-ish worked-example format: a specific, plain-language
// sentence for why this candidate landed at this rank — never "cannot
// perform this role", never "rejected". Transferable evidence is always
// called out separately from direct matches.
function whyRankedSentence(c: RankedCandidate, totalCount: number): string {
  if (c.ranking_status === "human_review_required") {
    return `Ranked #${c.rank} of ${totalCount} — evidence review is required before this ranking can be treated as final; see the flags below.`;
  }
  const parts: string[] = [];
  parts.push(`Ranked #${c.rank} of ${totalCount} with a ${fmt(c.match_score)} evidence-backed match score`);
  if (c.must_have_coverage >= 80) parts.push(`strong coverage of must-have requirements (${fmt(c.must_have_coverage)}%)`);
  else if (c.must_have_coverage >= 40) parts.push(`partial coverage of must-have requirements (${fmt(c.must_have_coverage)}%)`);
  else parts.push(`required skills not directly evidenced in most areas (${fmt(c.must_have_coverage)}% coverage)`);
  if (c.transferability >= 20) parts.push(`meaningful transferable-skill signal (${fmt(c.transferability)}%)`);
  return parts.join(", ") + ".";
}

import { RadarChart } from "@/components/RadarChart";
import { PipelineWorkflow } from "@/components/PipelineWorkflow";

function ComparePanel({ candidates, onClose }: { candidates: RankedCandidate[]; onClose: () => void }) {
  const metrics: { key: keyof RankedCandidate; label: string }[] = [
    { key: "match_score", label: "Match score" },
    { key: "evidence_confidence", label: "Evidence confidence" },
    { key: "document_integrity", label: "Document integrity" },
    { key: "must_have_coverage", label: "Must-have coverage" },
    { key: "transferability", label: "Transferability" },
  ];

  const sorted = [...candidates].sort((a, b) => a.rank - b.rank);
  const top = sorted[0];

  return (
    <Card className="p-6 mb-6 border-accent/40 bg-gradient-to-br from-white via-indigo-50/20 to-white shadow-md">
      <div className="flex items-center justify-between mb-5 pb-3 border-b border-border">
        <div>
          <h2 className="font-display font-bold text-base text-ink-900 flex items-center gap-2">
            <span>🎯</span> Multi-Candidate Radar Matrix Comparison
          </h2>
          <p className="text-xs text-ink-500">
            Side-by-side evidence analysis across 5 multi-dimensional evaluation axes.
          </p>
        </div>
        <button onClick={onClose} className="px-3 py-1.5 rounded-lg bg-slate-100 text-xs font-bold text-ink-600 hover:bg-slate-200 transition-colors">
          Close Comparison ✕
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 items-center">
        {/* Radar Chart Overlay */}
        <div className="flex justify-center bg-white p-4 rounded-2xl border border-border/80 shadow-xs">
          <RadarChart candidates={sorted} size={300} />
        </div>

        {/* Metrics Table & Explanations */}
        <div className="space-y-4">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-400 text-xs uppercase tracking-wide border-b border-border">
                  <th className="py-2 pr-4 font-medium">Metric</th>
                  {sorted.map((c) => (
                    <th key={c.application_id} className="py-2 pr-4 font-bold text-ink-900">
                      #{c.rank} {c.display_label}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {metrics.map((m) => (
                  <tr key={String(m.key)} className="border-t border-border/60">
                    <td className="py-2.5 pr-4 text-ink-500 text-xs font-medium">{m.label}</td>
                    {sorted.map((c) => (
                      <td key={c.application_id} className="py-2.5 pr-4 font-bold text-ink-900 text-xs">
                        {fmt(c[m.key] as number, 1)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="space-y-2 pt-2 border-t border-border/60">
            <h3 className="text-[11px] uppercase tracking-wider text-ink-400 font-bold">
              Why #{top.rank} ranks above the others
            </h3>
            {sorted.slice(1).map((c) => {
              const scoreDiff = top.match_score - c.match_score;
              const evidenceDiff = top.evidence_confidence - c.evidence_confidence;
              const coverageDiff = top.must_have_coverage - c.must_have_coverage;
              return (
                <p key={c.application_id} className="text-xs text-ink-600 leading-relaxed bg-white p-2.5 rounded-xl border border-slate-200">
                  <span className="text-ink-900 font-bold">
                    {top.display_label} ranks above {c.display_label}:
                  </span>{" "}
                  {scoreDiff >= 0 ? "+" : ""}
                  {scoreDiff.toFixed(1)} match score,{" "}
                  {evidenceDiff >= 0 ? "+" : ""}
                  {evidenceDiff.toFixed(1)} evidence confidence,{" "}
                  {coverageDiff >= 0 ? "+" : ""}
                  {coverageDiff.toFixed(1)}% must-have coverage.
                </p>
              );
            })}
          </div>
        </div>
      </div>
    </Card>
  );
}

function RankRow({
  c,
  totalCount,
  selected,
  onToggleSelect,
  onSetSelection,
  jobId,
}: {
  c: RankedCandidate;
  totalCount: number;
  selected: boolean;
  onToggleSelect: () => void;
  onSetSelection: (status: SelectionStatus) => void;
  jobId: string;
}) {
  const [expanded, setExpanded] = useState(false);
  const [savingSelection, setSavingSelection] = useState(false);

  async function handleSelect(status: SelectionStatus) {
    setSavingSelection(true);
    try {
      await onSetSelection(status);
    } finally {
      setSavingSelection(false);
    }
  }

  return (
    <>
      <tr className="border-t border-border hover:bg-surface-raised/40 transition-colors">
        <td className="py-3 pl-4 pr-2">
          <input
            type="checkbox"
            checked={selected}
            onChange={onToggleSelect}
            className="rounded border-border-strong text-accent focus:ring-accent/30"
          />
        </td>
        <td className="py-3 pr-4 font-display font-semibold text-ink-900">#{c.rank}</td>
        <td className="py-3 pr-4 min-w-[10rem]">
          <button onClick={() => setExpanded((e) => !e)} className="text-left">
            <div className="font-medium text-ink-900 hover:text-accent transition-colors">{c.display_label}</div>
          </button>
        </td>
        <td className="py-3 pr-4 font-medium text-ink-900">{fmt(c.match_score, 1)}</td>
        <td className="py-3 pr-4 text-ink-700">{fmt(c.evidence_confidence, 1)}</td>
        <td className="py-3 pr-4 text-ink-700">{fmt(c.document_integrity, 1)}</td>
        <td className="py-3 pr-4 text-ink-700">{fmt(c.must_have_coverage, 0)}%</td>
        <td className="py-3 pr-4 text-ink-700">{fmt(c.transferability, 0)}%</td>
        <td className="py-3 pr-4">
          <RankingStatusBadge status={c.ranking_status} />
        </td>
        <td className="py-3 pr-4">
          <SelectionStatusBadge status={c.selection_status} />
        </td>
        <td className="py-3 pr-4">
          <div className="flex items-center gap-1.5 flex-wrap">
            <Link href={`/dashboard/jobs/${jobId}/candidates/${c.application_id}`}>
              <Button size="sm" variant="secondary">
                View analysis
              </Button>
            </Link>
            <Button
              size="sm"
              variant={c.selection_status === "selected" ? "accent" : "primary"}
              disabled={savingSelection}
              onClick={() => handleSelect(c.selection_status === "selected" ? "not_selected" : "selected")}
            >
              {c.selection_status === "selected" ? "Selected ✓" : "Select for next stage"}
            </Button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-t border-border bg-surface-raised/30">
          <td colSpan={11} className="px-4 py-4">
            <div className="grid md:grid-cols-2 gap-5">
              <div>
                {c.top_strengths.length > 0 && (
                  <div className="mb-3">
                    <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
                      Strong evidence
                    </div>
                    <ul className="space-y-1">
                      {c.top_strengths.map((s) => (
                        <li key={s} className="text-sm text-ink-700 flex items-start gap-1.5">
                          <span className="text-success">✓</span> {s}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {c.transferability >= 15 && (
                  <div>
                    <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
                      Transferable signal
                    </div>
                    <p className="text-sm text-ink-700 flex items-start gap-1.5">
                      <span className="text-warning">~</span> {fmt(c.transferability, 0)}% transferable-skill
                      coverage — related experience, not a direct match. Labeled TRANSFERABLE, not MATCH.
                    </p>
                  </div>
                )}
                {c.major_gaps.length > 0 && (
                  <div className="mt-3">
                    <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
                      Required skill not directly evidenced
                    </div>
                    <ul className="space-y-1">
                      {c.major_gaps.map((g) => (
                        <li key={g} className="text-sm text-ink-500 flex items-start gap-1.5">
                          <span className="text-ink-300">–</span> {g}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
              <div>
                <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
                  Why ranked #{c.rank}
                </div>
                <p className="text-sm text-ink-500 leading-relaxed">{whyRankedSentence(c, totalCount)}</p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}

export default function JobRankingPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [data, setData] = useState<JobRankingResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [comparing, setComparing] = useState(false);
  const [blindMode, setBlindMode] = useState(true);

  const load = useCallback(() => {
    api
      .get<JobRankingResponse>(`/api/jobs/${jobId}/ranking?blind=${blindMode}`)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? e.message : "Could not load the ranking."));
  }, [jobId, blindMode]);

  useEffect(() => {
    load();
  }, [load]);

  async function setSelection(applicationId: string, status: SelectionStatus) {
    await api.post(`/api/applications/${applicationId}/selection`, { selection_status: status });
    load();
  }

  function toggleCompare(id: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else if (next.size < 4) next.add(id);
      return next;
    });
  }

  const compareCandidates = useMemo(
    () => (data ? data.ranking.filter((c) => selectedIds.has(c.application_id)) : []),
    [data, selectedIds]
  );

  if (error) {
    return <p className="text-sm text-danger">{error}</p>;
  }

  if (!data) {
    return (
      <div className="flex justify-center py-20 text-ink-400">
        <Spinner className="w-6 h-6" />
      </div>
    );
  }

  const { summary, ranking } = data;

  return (
    <div>
      <PageHeader
        title={`AI Ranking — ${data.job_title}`}
        description="Synthetix HR analyzes every candidate against the job requirements and produces an evidence-backed ranking so recruiters can focus their attention where it matters."
        actions={
          <div className="flex items-center gap-4">
            <label className="flex items-center gap-2 text-sm text-ink-600 font-medium cursor-pointer select-none bg-slate-100 px-3 py-1.5 rounded-xl border border-slate-200">
              <input
                type="checkbox"
                checked={blindMode}
                onChange={(e) => setBlindMode(e.target.checked)}
                className="rounded border-border-strong text-primary focus:ring-primary/30"
              />
              Blind review mode ({blindMode ? "ON - Candidate #Count" : "OFF - Person Names"})
            </label>
            <Link href={`/dashboard/jobs/${jobId}`}>
              <Button variant="secondary" size="sm">
                Candidate list view
              </Button>
            </Link>
          </div>
        }
      />

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card className="p-5">
          <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">Top match</div>
          <div className="font-display text-lg font-semibold text-ink-900 truncate">
            {summary.top_match_label ?? "—"}
          </div>
        </Card>
        <Card className="p-5">
          <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">Average match</div>
          <div className="font-display text-lg font-semibold text-ink-900">{fmt(summary.average_match, 1)}</div>
        </Card>
        <Card className="p-5">
          <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
            Highest evidence confidence
          </div>
          <div className="font-display text-lg font-semibold text-ink-900">
            {fmt(summary.highest_evidence_confidence, 1)}
          </div>
        </Card>
        <Card className="p-5">
          <div className="text-xs uppercase tracking-wide text-ink-400 font-medium mb-1.5">
            Candidates requiring review
          </div>
          <div className="font-display text-lg font-semibold text-ink-900">{summary.candidates_requiring_review}</div>
        </Card>
      </div>

      {comparing && compareCandidates.length >= 2 && (
        <ComparePanel candidates={compareCandidates} onClose={() => setComparing(false)} />
      )}

      {ranking.length === 0 ? (
        <Card>
          <EmptyState
            title="No ranked candidates yet"
            description="Upload and analyze resumes from the candidate list view — every analyzed candidate will appear here, ranked by evidence-backed match score."
          />
        </Card>
      ) : (
        <Card className="overflow-hidden">
          <div className="flex items-center justify-between px-5 py-4 border-b border-border">
            <div>
              <h2 className="font-display font-semibold text-ink-900">Ranked candidate pool</h2>
              <p className="text-xs text-ink-400 mt-0.5">
                Ordered by match score, then evidence confidence, then document integrity — never arbitrary.
              </p>
            </div>
            <Button
              size="sm"
              variant="accent"
              disabled={selectedIds.size < 2}
              onClick={() => setComparing(true)}
            >
              Compare selected ({selectedIds.size})
            </Button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-400 text-xs uppercase tracking-wide">
                  <th className="py-2.5 pl-4 pr-2 font-medium"></th>
                  <th className="py-2.5 pr-4 font-medium">Rank</th>
                  <th className="py-2.5 pr-4 font-medium">Candidate</th>
                  <th className="py-2.5 pr-4 font-medium">Match</th>
                  <th className="py-2.5 pr-4 font-medium">Evidence</th>
                  <th className="py-2.5 pr-4 font-medium">Integrity</th>
                  <th className="py-2.5 pr-4 font-medium">Must-have</th>
                  <th className="py-2.5 pr-4 font-medium">Transferable</th>
                  <th className="py-2.5 pr-4 font-medium">Status</th>
                  <th className="py-2.5 pr-4 font-medium">Selection</th>
                  <th className="py-2.5 pr-4 font-medium">Action</th>
                </tr>
              </thead>
              <tbody>
                {ranking.map((c) => (
                  <RankRow
                    key={c.application_id}
                    c={c}
                    totalCount={ranking.length}
                    jobId={jobId}
                    selected={selectedIds.has(c.application_id)}
                    onToggleSelect={() => toggleCompare(c.application_id)}
                    onSetSelection={(status) => setSelection(c.application_id, status)}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
    </div>
  );
}
