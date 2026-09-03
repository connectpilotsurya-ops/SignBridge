"use client";

import { useState } from "react";
import type { InterviewQuestion } from "@/types/api";

export function InterviewSimulator({
  questions = [],
  candidateName = "Candidate",
}: {
  questions?: InterviewQuestion[];
  candidateName?: string;
}) {
  const [selectedIdx, setSelectedIdx] = useState<number>(0);
  const [simulatedAnswers, setSimulatedAnswers] = useState<Record<number, string>>({});
  const [generating, setGenerating] = useState<boolean>(false);
  const [recruiterNotes, setRecruiterNotes] = useState<Record<number, string>>({});

  const activeQ = questions[selectedIdx];

  function handleSimulateAnswer(idx: number) {
    setGenerating(true);
    setTimeout(() => {
      const q = questions[idx];
      let ans = `Based on my experience, when working on ${q?.requirement || "this requirement"}, I focus on clear architecture and empirical evidence.`;
      if (q?.expected_signal) {
        ans += ` Specifically regarding ${q.expected_signal.toLowerCase()}, I delivered measurable performance outcomes in production environments.`;
      }
      setSimulatedAnswers((prev) => ({ ...prev, [idx]: ans }));
      setGenerating(false);
    }, 600);
  }

  if (questions.length === 0) {
    return (
      <div className="p-6 text-center bg-slate-50 rounded-2xl border border-dashed border-slate-200 text-xs text-ink-400">
        No targeted interview questions generated for this candidate fit.
      </div>
    );
  }

  return (
    <div className="bg-white rounded-2xl border border-border/80 p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between pb-3 border-b border-border">
        <div>
          <h3 className="font-display font-bold text-base text-ink-900 flex items-center gap-2">
            <span>🎙️</span> AI Candidate Sounding Board & Interview Simulator
          </h3>
          <p className="text-xs text-ink-500 mt-0.5">
            Requirements-based interview questions generated directly from candidate evidence gaps.
          </p>
        </div>
        <span className="px-2.5 py-1 rounded-full bg-primary-soft text-primary font-bold text-xs">
          {questions.length} Targeted Questions
        </span>
      </div>

      {/* Main Layout: Question Picker + Simulator Card */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Question Selector list */}
        <div className="space-y-2 md:col-span-1 border-r border-border/60 pr-0 md:pr-4">
          <div className="text-[11px] font-bold text-ink-400 uppercase tracking-wider mb-2">
            Target Questions
          </div>
          {questions.map((q, idx) => (
            <button
              key={idx}
              onClick={() => setSelectedIdx(idx)}
              className={`w-full text-left p-3 rounded-xl border text-xs transition-all ${
                selectedIdx === idx
                  ? "bg-primary-soft text-primary font-semibold border-primary/40 shadow-xs"
                  : "bg-slate-50 text-ink-700 border-slate-200/80 hover:bg-slate-100"
              }`}
            >
              <div className="font-bold text-[11px] text-ink-900 mb-1 flex items-center justify-between">
                <span>Question #{idx + 1}</span>
                <span className="text-[10px] text-ink-400 font-normal capitalize">
                  {q.type || "technical"}
                </span>
              </div>
              <p className="line-clamp-2 text-ink-600">{q.question}</p>
            </button>
          ))}
        </div>

        {/* Selected Question Detail & Mock Answer Simulator */}
        {activeQ && (
          <div className="md:col-span-2 space-y-4">
            <div className="p-4 bg-slate-50 rounded-xl border border-slate-200/80 space-y-2">
              <div className="flex items-center gap-2 text-xs font-bold text-primary">
                <span>📍 Target Requirement:</span>
                <span className="bg-primary/10 px-2 py-0.5 rounded text-primary">{activeQ.requirement}</span>
              </div>
              <h4 className="font-display font-bold text-sm text-ink-900">{activeQ.question}</h4>
              {activeQ.expected_signal && (
                <p className="text-xs text-ink-500 bg-white p-2.5 rounded-lg border border-slate-200">
                  <span className="font-semibold text-ink-700">Expected Signal to Listen For:</span>{" "}
                  {activeQ.expected_signal}
                </p>
              )}
            </div>

            {/* Simulated Candidate Response */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-ink-700 flex items-center gap-1.5">
                  <span>💬</span> Mock Candidate Response ({candidateName})
                </span>
                <button
                  onClick={() => handleSimulateAnswer(selectedIdx)}
                  disabled={generating}
                  className="px-3 py-1.5 rounded-lg bg-primary text-white text-xs font-semibold shadow-xs hover:bg-primary-hover transition-colors disabled:opacity-50"
                >
                  {generating ? "Generating..." : "Simulate Response ⚡"}
                </button>
              </div>

              {simulatedAnswers[selectedIdx] ? (
                <div className="p-3.5 bg-indigo-50/60 rounded-xl border border-indigo-200/60 text-xs text-indigo-950 leading-relaxed font-sans">
                  &quot;{simulatedAnswers[selectedIdx]}&quot;
                </div>
              ) : (
                <div className="p-4 text-center bg-slate-50/50 rounded-xl border border-dashed border-slate-200 text-xs text-ink-400">
                  Click &quot;Simulate Response&quot; to test how candidate evidence translates into an interview answer.
                </div>
              )}
            </div>

            {/* Recruiter Evaluation Notes */}
            <div className="space-y-1.5 pt-2">
              <label className="text-[11px] font-bold text-ink-600 uppercase tracking-wider block">
                Recruiter Interview Notes
              </label>
              <textarea
                rows={2}
                value={recruiterNotes[selectedIdx] || ""}
                onChange={(e) =>
                  setRecruiterNotes({ ...recruiterNotes, [selectedIdx]: e.target.value })
                }
                placeholder="Type your feedback, observations, or follow-up questions during the interview..."
                className="w-full p-2.5 rounded-xl border border-slate-200 text-xs text-ink-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
