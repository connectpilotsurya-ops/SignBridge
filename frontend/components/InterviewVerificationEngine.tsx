"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type {
  VerificationSummaryPayload,
  VerificationRecordStatus,
  CandidateStatus,
} from "@/types/api";
import { Pill, Spinner } from "./ui";
import { AIProctoredVideoCall } from "./AIProctoredVideoCall";

const FINAL_STATUS_OPTIONS: { label: string; value: CandidateStatus; tone: "success" | "primary" | "warning" | "danger" }[] = [
  { label: "Hire / Strong Match", value: "strong_match", tone: "success" },
  { label: "Potential Match (Next Round)", value: "potential_match", tone: "primary" },
  { label: "Needs Further Review", value: "review_required", tone: "warning" },
  { label: "Do Not Pursue (Low Match)", value: "low_match", tone: "danger" },
];

export function InterviewVerificationEngine({
  applicationId,
  onDecisionUpdated,
}: {
  applicationId: string;
  onDecisionUpdated?: () => void;
}) {
  const [data, setData] = useState<VerificationSummaryPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [notesInput, setNotesInput] = useState<Record<string, string>>({});
  const [submittingId, setSubmittingId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  // Final Decision & Video Call Modal State
  const [showFinalizeModal, setShowFinalizeModal] = useState(false);
  const [showVideoCallModal, setShowVideoCallModal] = useState(false);
  const [finalStatusChoice, setFinalStatusChoice] = useState<CandidateStatus>("strong_match");
  const [finalInterviewNotes, setFinalInterviewNotes] = useState("");
  const [submittingFinal, setSubmittingFinal] = useState(false);

  useEffect(() => {
    api
      .get<VerificationSummaryPayload>(
        `/api/applications/${applicationId}/verification/summary`
      )
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [applicationId]);

  const handleCopyQuestion = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleVerifySubmit = async (
    questionId: string,
    claimId: string | null,
    status: VerificationRecordStatus
  ) => {
    setSubmittingId(questionId);
    setMessage(null);
    try {
      await api.post(`/api/verification/questions/${questionId}/verify`, {
        verification_status: status,
        verification_notes: notesInput[questionId] || "",
      });
      setMessage("Question verification recorded.");
      const refreshed = await api.get<VerificationSummaryPayload>(
        `/api/applications/${applicationId}/verification/summary`
      );
      setData(refreshed);
    } catch {
      setMessage("Could not record question verification.");
    } finally {
      setSubmittingId(null);
    }
  };

  const handleFinalizeCandidateDecision = async (e: React.FormEvent) => {
    e.preventDefault();
    setSubmittingFinal(true);
    setMessage(null);
    try {
      await api.post(`/api/applications/${applicationId}/decision`, {
        decision: "override",
        final_status: finalStatusChoice,
        reason: finalInterviewNotes || "Final decision rendered after AI interview verification.",
      });
      setMessage(`🎯 Final interview decision submitted: Candidate updated to ${finalStatusChoice.replace(/_/g, " ").toUpperCase()}`);
      setShowFinalizeModal(false);
      if (onDecisionUpdated) onDecisionUpdated();
    } catch {
      setMessage("Failed to submit final decision.");
    } finally {
      setSubmittingFinal(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-8 text-ink-400">
        <Spinner className="w-6 h-6 text-primary" />
      </div>
    );
  }

  if (!data || data.claims.length === 0) {
    return (
      <div className="p-6 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-xs text-ink-400">
        No verification questions needed — all claims are strongly supported by evidence.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-border/80 p-5 shadow-sm space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">⚖️</span>
            <h3 className="font-display font-bold text-base text-ink-900">
              AI INTERVIEW VERIFICATION ENGINE
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-0.5">
            Converting claim-evidence gaps into targeted interview probes. Verify claims, then render final post-interview verdict.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => setShowVideoCallModal(true)}
            className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white font-bold text-xs shadow-sm transition-all flex items-center gap-1.5"
          >
            <span>🎥</span> Launch AI Proctored Video Call
          </button>
          <button
            onClick={() => setShowFinalizeModal(!showFinalizeModal)}
            className="px-3.5 py-1.5 rounded-xl bg-primary text-white font-bold text-xs shadow-sm hover:opacity-95 transition-all flex items-center gap-1.5"
          >
            <span>🎯</span> Finalize Candidate Decision
          </button>
        </div>
      </div>

      {message && (
        <div className="p-3 bg-emerald-50 text-emerald-800 text-xs font-semibold rounded-xl border border-emerald-200">
          ✅ {message}
        </div>
      )}

      {/* Finalize Candidate Modal / Panel */}
      {showFinalizeModal && (
        <form
          onSubmit={handleFinalizeCandidateDecision}
          className="p-5 bg-slate-900 text-white rounded-xl border border-slate-800 space-y-4 shadow-xl animate-in fade-in"
        >
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="font-display font-bold text-sm text-amber-400 flex items-center gap-2">
              <span>🎯</span> Finalize Candidate Post-Interview Decision
            </div>
            <button
              type="button"
              onClick={() => setShowFinalizeModal(false)}
              className="text-xs text-slate-400 hover:text-white"
            >
              ✕ Close
            </button>
          </div>

          <p className="text-xs text-slate-300">
            Select the final hiring verdict after completing your interview & verification checks.
          </p>

          <div className="space-y-2">
            <label className="block text-xs font-bold text-slate-300">Final Hiring Status:</label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {FINAL_STATUS_OPTIONS.map((opt) => (
                <button
                  type="button"
                  key={opt.value}
                  onClick={() => setFinalStatusChoice(opt.value)}
                  className={`p-3 rounded-lg text-xs font-bold border text-left transition-all ${
                    finalStatusChoice === opt.value
                      ? "bg-primary text-white border-primary ring-2 ring-primary/40"
                      : "bg-slate-800/80 text-slate-300 border-slate-700 hover:bg-slate-800"
                  }`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-1">
            <label className="block text-xs font-bold text-slate-300">
              Post-Interview Recruiter Assessment & Reason:
            </label>
            <textarea
              rows={3}
              value={finalInterviewNotes}
              onChange={(e) => setFinalInterviewNotes(e.target.value)}
              placeholder="e.g. Candidate demonstrated strong hands-on Kubernetes architecture in live coding. Verified ownership across all 3 production clusters."
              className="w-full p-2.5 rounded-lg bg-slate-800 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:ring-1 focus:ring-primary"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={() => setShowFinalizeModal(false)}
              className="px-3 py-1.5 rounded-lg bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submittingFinal}
              className="px-4 py-1.5 rounded-lg bg-emerald-500 text-slate-950 font-bold text-xs hover:bg-emerald-400 transition-colors shadow-md"
            >
              {submittingFinal ? "Submitting Final Verdict..." : "Submit Final Hiring Decision 🎯"}
            </button>
          </div>
        </form>
      )}

      {/* Claims Breakdown Cards */}
      <div className="space-y-4">
        <div className="text-xs font-bold text-ink-700 uppercase tracking-wider">
          Claim Evidence & Gap Analysis:
        </div>
        {data.claims.map((claim) => (
          <div
            key={claim.id}
            className="p-4 bg-slate-50/80 rounded-xl border border-slate-200/90 space-y-3"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="font-bold text-sm text-ink-900">{claim.skill}</div>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-ink-500 font-medium">
                  Evidence Level:
                </span>
                <Pill
                  tone={
                    claim.evidence_level === "VERY_STRONG" ||
                    claim.evidence_level === "STRONG"
                      ? "success"
                      : claim.evidence_level === "MODERATE"
                      ? "primary"
                      : "warning"
                  }
                >
                  {claim.evidence_level.replace("_", " ")}
                </Pill>
              </div>
            </div>

            {claim.consistency_note && (
              <p className="text-xs text-ink-600 bg-white p-2.5 rounded-lg border border-slate-200">
                {claim.consistency_note}
              </p>
            )}

            {/* Gap warning badges */}
            {claim.evidence_gaps.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pt-1">
                {claim.evidence_gaps.map((gap, idx) => (
                  <span
                    key={idx}
                    className="inline-flex items-center gap-1 text-[10px] font-bold text-amber-800 bg-amber-100/80 px-2 py-0.5 rounded-md border border-amber-200"
                  >
                    <span>⚠️</span> {gap.replace(/_/g, " ")}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Targeted Verification Questions List */}
      <div className="space-y-4 pt-2">
        <div className="flex items-center justify-between">
          <div className="text-xs font-bold text-ink-700 uppercase tracking-wider">
            Suggested Verification Questions ({data.questions.length})
          </div>
          <button
            onClick={() => {
              const allQ = data.questions.map((q) => q.question).join("\n\n");
              navigator.clipboard.writeText(allQ);
              setCopiedId("all");
              setTimeout(() => setCopiedId(null), 2000);
            }}
            className="px-3 py-1 rounded-lg bg-slate-100 text-ink-600 hover:text-ink-900 text-xs font-semibold border border-slate-200 transition-colors"
          >
            {copiedId === "all" ? "Copied All! ✓" : "Copy All Questions 📋"}
          </button>
        </div>

        <div className="space-y-3">
          {data.questions.map((q, idx) => {
            const isVerified = q.status === "verified";
            return (
              <div
                key={q.id}
                className={`p-4 rounded-xl border transition-all space-y-3 ${
                  isVerified
                    ? "bg-emerald-50/60 border-emerald-200"
                    : "bg-white border-slate-200 shadow-xs"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-primary bg-primary-soft px-2 py-0.5 rounded">
                      0{idx + 1}
                    </span>
                    <span className="font-bold text-xs uppercase tracking-wider text-ink-700">
                      {q.verification_category}
                    </span>
                  </div>
                  <span
                    className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full ${
                      isVerified
                        ? "bg-emerald-100 text-emerald-800"
                        : "bg-slate-100 text-slate-600"
                    }`}
                  >
                    {q.status}
                  </span>
                </div>

                <div className="font-display font-semibold text-xs text-ink-900 leading-relaxed">
                  {q.question}
                </div>

                {q.purpose && (
                  <div className="text-[11px] text-ink-500">
                    <span className="font-bold text-ink-700">Purpose:</span> {q.purpose}
                  </div>
                )}

                {/* Recruiter Verification Input & Action */}
                <div className="pt-2 border-t border-slate-100 space-y-2">
                  <input
                    type="text"
                    value={notesInput[q.id] ?? q.recruiter_notes ?? ""}
                    onChange={(e) =>
                      setNotesInput({ ...notesInput, [q.id]: e.target.value })
                    }
                    placeholder="Recruiter notes during interview..."
                    className="w-full p-2 rounded-lg border border-slate-200 text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                  />

                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <button
                      onClick={() => handleCopyQuestion(q.id, q.question)}
                      className="text-[11px] font-semibold text-primary hover:underline"
                    >
                      {copiedId === q.id ? "Copied! ✓" : "Copy Question"}
                    </button>

                    <div className="flex items-center gap-1.5">
                      <button
                        onClick={() =>
                          handleVerifySubmit(q.id, q.claim_id, "verified")
                        }
                        disabled={submittingId === q.id}
                        className="px-2.5 py-1 rounded bg-emerald-600 text-white font-bold text-[10px] hover:bg-emerald-700 transition-colors"
                      >
                        ✓ Mark Verified
                      </button>
                      <button
                        onClick={() =>
                          handleVerifySubmit(q.id, q.claim_id, "not_verified")
                        }
                        disabled={submittingId === q.id}
                        className="px-2.5 py-1 rounded bg-rose-600 text-white font-bold text-[10px] hover:bg-rose-700 transition-colors"
                      >
                        ✕ Unverified
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {showVideoCallModal && (
        <AIProctoredVideoCall
          candidateName="Candidate"
          jobTitle="Engineering Role"
          questions={data.questions.map((q) => ({
            id: q.id,
            question: q.question,
            category: q.verification_category,
            purpose: q.purpose,
          }))}
          onClose={() => setShowVideoCallModal(false)}
        />
      )}
    </div>
  );
}
