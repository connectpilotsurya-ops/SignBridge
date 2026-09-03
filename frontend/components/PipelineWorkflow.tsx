"use client";

import { useState } from "react";
import type { RankedCandidate, SelectionStatus } from "@/types/api";

const STAGES: { id: string; label: string; tone: string }[] = [
  { id: "unreviewed", label: "Ranked Pool", tone: "border-l-indigo-500" },
  { id: "under_review", label: "Recruiter Review", tone: "border-l-amber-500" },
  { id: "selected", label: "Selected for Next Stage", tone: "border-l-emerald-500" },
  { id: "not_selected", label: "Archive / On Hold", tone: "border-l-slate-400" },
];

export function PipelineWorkflow({
  candidates = [],
  onSetSelection,
}: {
  candidates: RankedCandidate[];
  onSetSelection: (candidateId: string, status: SelectionStatus) => void;
}) {
  const [activeStage, setActiveStage] = useState<string>("all");

  const getStageCandidates = (stageId: string) => {
    if (stageId === "unreviewed") {
      return candidates.filter((c) => !c.selection_status || c.selection_status === "under_review");
    }
    if (stageId === "under_review") {
      return candidates.filter((c) => c.selection_status === "under_review");
    }
    if (stageId === "selected") {
      return candidates.filter((c) => c.selection_status === "selected");
    }
    if (stageId === "not_selected") {
      return candidates.filter((c) => c.selection_status === "not_selected");
    }
    return candidates;
  };

  return (
    <div className="bg-white rounded-2xl border border-border/80 p-5 shadow-sm space-y-4">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-border">
        <div>
          <h3 className="font-display font-bold text-base text-ink-900 flex items-center gap-2">
            <span>📋</span> Interactive Candidate Recruitment Pipeline Workflow
          </h3>
          <p className="text-xs text-ink-500 mt-0.5">
            Organize candidates into hiring stages without modifying deterministic AI ranks or evidence scores.
          </p>
        </div>

        {/* Stage Filter Selector */}
        <div className="flex items-center gap-1 bg-slate-100 p-1 rounded-xl text-xs font-semibold">
          <button
            onClick={() => setActiveStage("all")}
            className={`px-3 py-1.5 rounded-lg transition-all ${
              activeStage === "all" ? "bg-white text-primary shadow-xs" : "text-ink-500 hover:text-ink-900"
            }`}
          >
            All Candidates ({candidates.length})
          </button>
          {STAGES.map((s) => {
            const count = getStageCandidates(s.id).length;
            return (
              <button
                key={s.id}
                onClick={() => setActiveStage(s.id)}
                className={`px-3 py-1.5 rounded-lg transition-all ${
                  activeStage === s.id ? "bg-white text-primary shadow-xs" : "text-ink-500 hover:text-ink-900"
                }`}
              >
                {s.label} ({count})
              </button>
            );
          })}
        </div>
      </div>

      {/* Grid Columns for Hiring Stages */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {STAGES.filter((s) => activeStage === "all" || activeStage === s.id).map((stage) => {
          const list = getStageCandidates(stage.id);
          return (
            <div key={stage.id} className="bg-slate-50/70 p-4 rounded-xl border border-slate-200/80 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-200 pb-2">
                <span className="font-display font-bold text-xs text-ink-900 flex items-center gap-1.5">
                  <span className={`w-2.5 h-2.5 rounded-full ${stage.id === "selected" ? "bg-emerald-500" : stage.id === "under_review" ? "bg-amber-500" : "bg-indigo-500"}`} />
                  {stage.label}
                </span>
                <span className="text-[11px] font-extrabold text-ink-500 px-2 py-0.5 rounded-md bg-white border border-slate-200">
                  {list.length}
                </span>
              </div>

              {list.length === 0 ? (
                <div className="p-4 text-center text-xs text-ink-400 italic">No candidates in this stage.</div>
              ) : (
                <div className="space-y-2.5">
                  {list.map((c) => (
                    <div
                      key={c.application_id}
                      className={`p-3 bg-white rounded-xl border border-slate-200/90 shadow-xs hover:shadow-md transition-all space-y-2 border-l-4 ${stage.tone}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-xs text-ink-900">
                          #{c.rank} {c.display_label}
                        </span>
                        <span className="font-mono text-xs font-bold text-primary">
                          {c.match_score.toFixed(0)} pts
                        </span>
                      </div>

                      <div className="flex items-center justify-between text-[11px] text-ink-500">
                        <span>Confidence: {c.evidence_confidence.toFixed(0)}%</span>
                        <span>Integrity: {c.document_integrity.toFixed(0)}%</span>
                      </div>

                      {/* Quick Action Selection Buttons */}
                      <div className="flex items-center gap-1.5 pt-1 border-t border-slate-100">
                        {stage.id !== "selected" && (
                          <button
                            onClick={() => onSetSelection(c.application_id, "selected")}
                            className="flex-1 py-1 rounded bg-emerald-50 text-emerald-700 hover:bg-emerald-100 font-bold text-[10px] transition-colors"
                          >
                            + Select for Stage
                          </button>
                        )}
                        {stage.id !== "not_selected" && (
                          <button
                            onClick={() => onSetSelection(c.application_id, "not_selected")}
                            className="py-1 px-2.5 rounded bg-slate-100 text-slate-600 hover:bg-slate-200 font-bold text-[10px] transition-colors"
                          >
                            Hold
                          </button>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
