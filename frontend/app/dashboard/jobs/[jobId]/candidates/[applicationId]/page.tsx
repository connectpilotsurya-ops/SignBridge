"use client";

import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CandidateAnalysis, CandidateStatus } from "@/types/api";
import {
  Button,
  Card,
  CandidateStatusBadge,
  IntegrityBadge,
  MatchStatusBadge,
  Pill,
  ScoreBar,
  ScoreGauge,
  Spinner,
  TextArea,
} from "@/components/ui";
import { CapabilityGraph } from "@/components/CapabilityGraph";
import { PdfInspector } from "@/components/PdfInspector";
import { InterviewSimulator } from "@/components/InterviewSimulator";
import { InterviewVerificationEngine } from "@/components/InterviewVerificationEngine";



const FINAL_STATUS_OPTIONS: CandidateStatus[] = [
  "strong_match",
  "potential_match",
  "review_required",
  "low_match",
];

function Section({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <Card className="p-6 mb-6">
      <h2 className="font-display font-semibold text-ink-900">{title}</h2>
      {subtitle && <p className="text-sm text-ink-500 mt-0.5 mb-4">{subtitle}</p>}
      {!subtitle && <div className="mb-4" />}
      {children}
    </Card>
  );
}

export default function CandidateDetailPage() {
  const { applicationId } = useParams<{ jobId: string; applicationId: string }>();
  const [analysis, setAnalysis] = useState<CandidateAnalysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [blindMode, setBlindMode] = useState(true);

  const [decision, setDecision] = useState<"agree" | "override" | "needs_further_review">("agree");
  const [finalStatus, setFinalStatus] = useState<CandidateStatus>("potential_match");
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [decisionResult, setDecisionResult] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<CandidateAnalysis>(`/api/applications/${applicationId}?blind=${blindMode}`)
      .then((data) => {
        setAnalysis(data);
        setFinalStatus(data.status);
      })
      .catch((e) => setError(e.message));
  }, [applicationId, blindMode]);

  async function handleDecisionSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setDecisionResult(null);
    setError(null);
    try {
      const body: Record<string, unknown> = { decision };
      if (decision === "override") {
        body.final_status = finalStatus;
        body.reason = reason;
      }
      const result = await api.post<{ original_status: string; final_status: string }>(
        `/api/applications/${applicationId}/decision`,
        body
      );
      setDecisionResult(
        `Recorded: ${result.original_status.replace("_", " ")} → ${result.final_status.replace("_", " ")}.`
      );
      const refreshed = await api.get<CandidateAnalysis>(`/api/applications/${applicationId}?blind=${blindMode}`);
      setAnalysis(refreshed);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not submit decision.");
    } finally {
      setSubmitting(false);
    }
  }

  if (error && !analysis) return <p className="text-sm text-danger">{error}</p>;
  if (!analysis) {
    return (
      <div className="flex justify-center py-20 text-ink-400">
        <Spinner className="w-6 h-6" />
      </div>
    );
  }

  const a = analysis;

  return (
    <div className="max-w-3xl">
      <div className="flex items-start justify-between gap-4 mb-6">
        <div>
          <div className="flex items-center gap-2 flex-wrap mb-1">
            <h1 className="font-display text-2xl font-bold text-ink-900">{a.display_label}</h1>
            <CandidateStatusBadge status={a.status} />
            <Pill tone={a.analysis_mode === "real" ? "accent" : "neutral"}>
              {a.analysis_mode === "real" ? "Gemini Analysis" : "Zero-LLM Fast Pass"}
            </Pill>
          </div>
          <label className="flex items-center gap-2 text-xs text-ink-500 font-medium cursor-pointer select-none">
            <input
              type="checkbox"
              checked={blindMode}
              onChange={(e) => setBlindMode(e.target.checked)}
              className="rounded border-border-strong text-primary focus:ring-primary/30"
            />
            Blind review mode ({blindMode ? "ON - Candidate #Count" : "OFF - Person Name Revealed"})
          </label>
        </div>

        <a
          href={`/interview/${applicationId}`}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-all"
        >
          <span>🌐</span> Open Candidate AI Interview Portal (3 Probes) ↗
        </a>
      </div>

      {a.analysis_incomplete && (
        <Card className="p-4 mb-6 border-danger/30 bg-danger-soft">
          <p className="text-sm text-danger font-medium">
            Analysis incomplete{a.incomplete_reason ? `: ${a.incomplete_reason}` : "."} This candidate requires
            manual review — nothing below should be treated as a completed assessment.
          </p>
        </Card>
      )}

      {a.human_review_required && (
        <Card className="p-4 mb-6 border-warning/30 bg-warning-soft">
          <p className="text-sm font-medium text-warning mb-1.5">Human review required</p>
          <ul className="text-sm text-ink-700 list-disc list-inside space-y-0.5">
            {a.human_review_reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        </Card>
      )}

      <Card className="p-6 mb-6">
        <div className="grid grid-cols-3 gap-4 mb-6">
          <ScoreGauge score={a.scores.match_score} label="Match score" />
          <ScoreGauge score={a.scores.evidence_confidence} label="Evidence confidence" />
          <ScoreGauge score={a.scores.document_integrity} label="Document integrity" />
        </div>
        <p className="text-sm text-ink-700 leading-relaxed mb-6">{a.executive_summary}</p>
        
        {/* Points Calculation Breakdown Table */}
        <div className="border-t border-border pt-5">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-bold text-ink-900 uppercase tracking-wider">
              📊 Calculated Score Breakdown (Points / Max Weight)
            </h3>
            <span className="text-xs font-bold text-primary">
              TOTAL: {a.scores.match_score.toFixed(1)} / 100
            </span>
          </div>

          <div className="overflow-x-auto mb-5 rounded-xl border border-border bg-surface-raised/30 p-3">
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-border/80 text-ink-400 font-semibold uppercase tracking-wider">
                  <th className="pb-2">Scoring Component</th>
                  <th className="pb-2 text-right">Points Earned</th>
                  <th className="pb-2 text-right">Max Weight</th>
                  <th className="pb-2 text-right">Score Share</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border/40 font-medium text-ink-800">
                <tr>
                  <td className="py-2 font-medium">Must-have Requirements</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.must_have_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.must_have_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.must_have_points / (a.scores.breakdown.must_have_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Preferred Requirements</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.preferred_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.preferred_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.preferred_points / (a.scores.breakdown.preferred_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Evidence Strength & Grounding</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.evidence_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.evidence_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.evidence_points / (a.scores.breakdown.evidence_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Experience Trajectory</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.experience_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.experience_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.experience_points / (a.scores.breakdown.experience_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Transferable Skills</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.transferability_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.transferability_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.transferability_points / (a.scores.breakdown.transferability_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Adaptability & Velocity</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.adaptability_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.adaptability_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.adaptability_points / (a.scores.breakdown.adaptability_max || 1)) * 100)}%</td>
                </tr>
                <tr>
                  <td className="py-2 font-medium">Document Integrity</td>
                  <td className="py-2 text-right font-bold text-ink-900">{a.scores.breakdown.integrity_points.toFixed(1)}</td>
                  <td className="py-2 text-right text-ink-400">/ {a.scores.breakdown.integrity_max}</td>
                  <td className="py-2 text-right text-ink-600 font-semibold">{Math.round((a.scores.breakdown.integrity_points / (a.scores.breakdown.integrity_max || 1)) * 100)}%</td>
                </tr>
                <tr className="border-t-2 border-ink-900 font-extrabold text-ink-900">
                  <td className="py-2.5">TOTAL MATCH SCORE</td>
                  <td className="py-2.5 text-right text-primary text-sm font-black">{a.scores.match_score.toFixed(1)}</td>
                  <td className="py-2.5 text-right text-sm text-ink-500">/ 100.0</td>
                  <td className="py-2.5 text-right text-sm text-primary">{Math.round(a.scores.match_score)}%</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-8 gap-y-3">
          <ScoreBar label="Must-have requirements" value={a.scores.breakdown.must_have_points} max={a.scores.breakdown.must_have_max} tone="primary" />
          <ScoreBar label="Preferred requirements" value={a.scores.breakdown.preferred_points} max={a.scores.breakdown.preferred_max} tone="accent" />
          <ScoreBar label="Evidence strength" value={a.scores.breakdown.evidence_points} max={a.scores.breakdown.evidence_max} tone="primary" />
          <ScoreBar label="Experience" value={a.scores.breakdown.experience_points} max={a.scores.breakdown.experience_max} tone="accent" />
          <ScoreBar label="Transferability" value={a.scores.breakdown.transferability_points} max={a.scores.breakdown.transferability_max} tone="primary" />
          <ScoreBar label="Adaptability" value={a.scores.breakdown.adaptability_points} max={a.scores.breakdown.adaptability_max} tone="accent" />
          <ScoreBar label="Document integrity" value={a.scores.breakdown.integrity_points} max={a.scores.breakdown.integrity_max} tone="primary" />
        </div>
      </Card>

      <Section title="Requirement-by-requirement evidence" subtitle="Every status is traced back to specific text in the resume — never an unexplained number.">
        <div className="space-y-4">
          {a.requirement_analysis.map((r) => (
            <div key={r.requirement} className="border border-border rounded-xl p-4">
              <div className="flex items-center justify-between gap-3 mb-2">
                <span className="font-medium text-ink-900">{r.requirement}</span>
                <MatchStatusBadge status={r.status} />
              </div>
              {r.evidence.length > 0 && (
                <div className="space-y-1.5 mb-2">
                  {r.evidence.map((e, i) => (
                    <blockquote key={i} className="text-sm text-ink-600 border-l-2 border-border-strong pl-3">
                      &ldquo;{e.text}&rdquo;
                      <span className="text-ink-400"> — {e.source.replace(/_/g, " ")}{e.page ? `, p.${e.page}` : ""}</span>
                    </blockquote>
                  ))}
                </div>
              )}
              {r.explanation && <p className="text-sm text-ink-500">{r.explanation}</p>}
              {r.why_not && <p className="text-sm text-ink-500 mt-1">{r.why_not}</p>}
              {r.verification_needed && r.verification_question && (
                <p className="text-sm text-primary mt-2 bg-primary-soft rounded-lg px-3 py-2">
                  Ask the candidate: {r.verification_question}
                </p>
              )}
            </div>
          ))}
        </div>
      </Section>

      {a.claim_consistency.length > 0 && (
        <Section title="Claim-evidence consistency" subtitle="Checks whether specific claims are backed up elsewhere in the document — never an accusation, only a verification flag.">
          <div className="space-y-3">
            {a.claim_consistency.map((c, i) => (
              <div key={i} className="text-sm">
                <div className="flex items-center gap-2">
                  <Pill tone={c.status === "supported" ? "success" : c.status === "conflicting" ? "danger" : "warning"}>
                    {c.status}
                  </Pill>
                  <span className="text-ink-700">{c.claim}</span>
                </div>
                <p className="text-ink-500 mt-1 ml-1">{c.explanation}</p>
              </div>
            ))}
          </div>
        </Section>
      )}

      <Section title="Career trajectory & adaptability">
        {a.career_trajectory.points.length === 0 ? (
          <p className="text-sm text-ink-400">{a.career_trajectory.summary}</p>
        ) : (
          <>
            <p className="text-sm text-ink-500 mb-4">{a.career_trajectory.summary}</p>
            <ol className="relative border-l border-border ml-2 space-y-5">
              {a.career_trajectory.points.map((p, i) => (
                <li key={i} className="ml-4">
                  <div className="absolute -ml-[21px] h-2.5 w-2.5 rounded-full bg-primary mt-1.5" />
                  <div className="text-xs text-ink-400">{p.period_label}</div>
                  <div className="font-medium text-ink-900 text-sm">{p.role || "Role"}</div>
                  {p.technologies.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {p.technologies.map((t) => (
                        <Pill key={t} tone="neutral">
                          {t}
                        </Pill>
                      ))}
                    </div>
                  )}
                </li>
              ))}
            </ol>
          </>
        )}
        <div className="mt-5 pt-5 border-t border-border">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-ink-700">Adaptability</span>
            <Pill tone={a.adaptability.level === "high" ? "success" : a.adaptability.level === "moderate" ? "primary" : "neutral"}>
              {a.adaptability.level}
            </Pill>
          </div>
          <p className="text-sm text-ink-500">{a.adaptability.explanation}</p>
        </div>
      </Section>

      <Section title="Document Integrity & Forensic Inspection" subtitle="PyMuPDF forensic layer checks — zero LLM involvement.">
        <PdfInspector integrity={a.integrity} />
      </Section>

      <Section title="Capability Graph Visualizer" subtitle="A structural view of how each skill connects to a requirement and its supporting evidence.">
        <CapabilityGraph graph={a.capability_graph} />
      </Section>

      {a.interview_questions.length > 0 && (
        <Section title="AI Candidate Sounding Board" subtitle="Targeted at the requirements with the weakest direct evidence.">
          <InterviewSimulator questions={a.interview_questions} candidateName={a.display_label} />
        </Section>
      )}

      <div className="mb-6">
        <InterviewVerificationEngine
          applicationId={applicationId}
          onDecisionUpdated={() => {
            api
              .get<CandidateAnalysis>(`/api/applications/${applicationId}`)
              .then((data) => setAnalysis(data))
              .catch(() => {});
          }}
        />
      </div>

      <Section title="Recruiter decision" subtitle="The system's assessment is never overwritten — your call is recorded alongside it, permanently auditable.">
        <form onSubmit={handleDecisionSubmit} className="space-y-4">
          <div className="flex gap-2">
            {(["agree", "override", "needs_further_review"] as const).map((opt) => (
              <button
                type="button"
                key={opt}
                onClick={() => setDecision(opt)}
                className={`text-sm font-medium rounded-xl px-3.5 py-2 border transition-colors ${
                  decision === opt
                    ? "bg-primary text-bg border-primary"
                    : "bg-surface text-ink-600 border-border-strong hover:bg-bg"
                }`}
              >
                {opt === "agree" ? "Agree with assessment" : opt === "override" ? "Override" : "Needs further review"}
              </button>
            ))}
          </div>

          {decision === "override" && (
            <div className="space-y-3">
              <label className="block">
                <span className="block text-sm font-medium text-ink-700 mb-1.5">Final status</span>
                <select
                  value={finalStatus}
                  onChange={(e) => setFinalStatus(e.target.value as CandidateStatus)}
                  className="w-full rounded-xl border border-border-strong bg-surface px-3.5 py-2.5 text-sm outline-none focus:border-primary focus:ring-2 focus:ring-primary/15"
                >
                  {FINAL_STATUS_OPTIONS.map((s) => (
                    <option key={s} value={s}>
                      {s.replace(/_/g, " ")}
                    </option>
                  ))}
                </select>
              </label>
              <TextArea
                label="Reason (required)"
                required
                rows={3}
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="e.g. Verified in a live technical interview despite the system flag."
              />
            </div>
          )}

          {error && <p className="text-sm text-danger">{error}</p>}
          {decisionResult && <p className="text-sm text-success">{decisionResult}</p>}

          <Button type="submit" disabled={submitting}>
            {submitting ? "Saving…" : "Submit decision"}
          </Button>
        </form>
      </Section>
    </div>
  );
}
