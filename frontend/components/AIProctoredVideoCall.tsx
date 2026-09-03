"use client";

import { useState } from "react";
import { Button, Card, Pill } from "@/components/ui";

interface AIProctoredVideoCallProps {
  candidateName: string;
  jobTitle: string;
  questions: { id: string; question: string; category: string; purpose?: string }[];
  onClose: () => void;
}

export function AIProctoredVideoCall({
  candidateName,
  jobTitle,
  questions,
  onClose,
}: AIProctoredVideoCallProps) {
  const [activeQuestionIdx, setActiveQuestionIdx] = useState(0);
  const [callState, setCallState] = useState<"lobby" | "in_call" | "evaluated">("lobby");
  const [simulatedScore, setSimulatedScore] = useState<number | null>(null);

  const currentQuestion = questions[activeQuestionIdx] || {
    question: "Walk through the architectural trade-offs of scaling your core database layer under heavy write concurrency.",
    category: "architecture",
    purpose: "Verify high-scale system design concepts & data consistency handling.",
  };

  function startCall() {
    setCallState("in_call");
  }

  function finishCall() {
    setSimulatedScore(91);
    setCallState("evaluated");
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/80 backdrop-blur-md p-4 overflow-y-auto">
      <Card className="w-full max-w-4xl bg-slate-950 text-white border-slate-800 shadow-2xl overflow-hidden rounded-3xl">
        {/* Top Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-900/60">
          <div className="flex items-center gap-3">
            <div className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse" />
            <div>
              <h2 className="font-display font-bold text-base text-white flex items-center gap-2">
                🤖 AI Candidate Sounding Board & Proctored Video Interview
              </h2>
              <p className="text-xs text-slate-400">
                Candidate: <span className="text-slate-200 font-semibold">{candidateName}</span> · Role: <span className="text-slate-200 font-semibold">{jobTitle}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Pill tone="success" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-xs">
              🛡️ Live AI Proctoring Active
            </Pill>
            <button
              onClick={onClose}
              className="text-slate-400 hover:text-white text-lg font-bold px-2 py-1 transition-colors"
            >
              ✕
            </button>
          </div>
        </div>

        {/* Call Lobby View */}
        {callState === "lobby" && (
          <div className="p-8 text-center space-y-6">
            <div className="w-20 h-20 rounded-3xl bg-indigo-600/20 border border-indigo-500/40 flex items-center justify-center mx-auto shadow-lg shadow-indigo-500/10">
              <span className="text-4xl">🎥</span>
            </div>

            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-xl font-bold font-display text-white">
                Initiate AI Proctored Knowledge Test
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                The interviewer approved candidate progression. Launch an autonomous, 1-on-1 AI video sounding board session to verify real technical depth with moderate to complex architectural probes.
              </p>
            </div>

            {/* Proctoring Checks Grid */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 max-w-2xl mx-auto pt-2">
              <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 text-left">
                <div className="text-xs font-bold text-indigo-400 mb-1 flex items-center gap-1.5">
                  👁️ Eye-Tracking & Gaze
                </div>
                <div className="text-[11px] text-slate-400">Monitors head posture & screen focus</div>
              </div>
              <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 text-left">
                <div className="text-xs font-bold text-emerald-400 mb-1 flex items-center gap-1.5">
                  🎙️ Acoustic Biometrics
                </div>
                <div className="text-[11px] text-slate-400">Verifies single voice speaker profile</div>
              </div>
              <div className="p-3 rounded-2xl bg-slate-900 border border-slate-800 text-left">
                <div className="text-xs font-bold text-amber-400 mb-1 flex items-center gap-1.5">
                  🧠 Sounding Board Engine
                </div>
                <div className="text-[11px] text-slate-400">Evaluates moderate technical depth</div>
              </div>
            </div>

            <div className="pt-4 flex justify-center gap-3">
              <Button variant="secondary" onClick={onClose} className="bg-slate-800 text-slate-300 border-slate-700 hover:bg-slate-700">
                Cancel
              </Button>
              <Button onClick={startCall} className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6 shadow-lg shadow-indigo-600/30">
                🚀 Start Proctored AI Video Call
              </Button>
            </div>
          </div>
        )}

        {/* Live Call Screen */}
        {callState === "in_call" && (
          <div className="p-6 space-y-6">
            {/* Video Feeds Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              {/* Candidate Video Frame */}
              <div className="relative aspect-video rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col justify-between p-4 shadow-inner">
                <div className="flex items-center justify-between z-10">
                  <span className="bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded-lg text-xs font-bold text-slate-200 border border-slate-800 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                    {candidateName} (Candidate Feed)
                  </span>
                  <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-emerald-500/30">
                    HD 1080p · 60fps
                  </span>
                </div>

                {/* Simulated Camera Video Content */}
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-t from-slate-950 via-slate-900 to-indigo-950/40">
                  <div className="w-24 h-24 rounded-full bg-slate-800 border-2 border-indigo-500/50 flex items-center justify-center shadow-2xl relative mb-2">
                    <span className="text-3xl font-bold text-slate-300">
                      {candidateName.split(" ").map((n) => n[0]).join("")}
                    </span>
                    <div className="absolute inset-0 rounded-full border border-emerald-400 animate-pulse" />
                  </div>
                  <span className="text-xs font-medium text-slate-400">Proctored Candidate Camera Active</span>

                  {/* Audio Waveform Animation */}
                  <div className="flex items-center gap-1 mt-3">
                    <div className="w-1 bg-indigo-500 h-4 animate-bounce" style={{ animationDelay: "0.1s" }} />
                    <div className="w-1 bg-indigo-500 h-7 animate-bounce" style={{ animationDelay: "0.2s" }} />
                    <div className="w-1 bg-indigo-500 h-3 animate-bounce" style={{ animationDelay: "0.3s" }} />
                    <div className="w-1 bg-indigo-500 h-8 animate-bounce" style={{ animationDelay: "0.4s" }} />
                    <div className="w-1 bg-indigo-500 h-5 animate-bounce" style={{ animationDelay: "0.5s" }} />
                  </div>
                </div>

                {/* Live Proctoring Overlay Signals */}
                <div className="z-10 flex items-center justify-between text-[11px] text-slate-400 bg-slate-950/90 p-2 rounded-xl border border-slate-800">
                  <span>Gaze: <strong className="text-emerald-400">Focused (100%)</strong></span>
                  <span>Audio: <strong className="text-emerald-400">Single Speaker</strong></span>
                  <span>Displays: <strong className="text-emerald-400">1 Verified</strong></span>
                </div>
              </div>

              {/* AI Sounding Board Interrogator Frame */}
              <div className="relative aspect-video rounded-2xl bg-slate-900 border border-slate-800 overflow-hidden flex flex-col justify-between p-4 shadow-inner">
                <div className="flex items-center justify-between z-10">
                  <span className="bg-indigo-950/90 backdrop-blur-md px-2.5 py-1 rounded-lg text-xs font-bold text-indigo-300 border border-indigo-800 flex items-center gap-2">
                    🤖 Synthetix AI Sounding Board
                  </span>
                  <span className="bg-indigo-500/20 text-indigo-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-indigo-500/30">
                    Moderate Difficulty Mode
                  </span>
                </div>

                {/* AI Avatar & Speech Indicator */}
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-t from-slate-950 via-indigo-950/30 to-slate-900">
                  <div className="w-24 h-24 rounded-3xl bg-indigo-600 flex items-center justify-center shadow-xl shadow-indigo-600/30 border border-indigo-400/30 mb-2">
                    <span className="text-4xl">🧠</span>
                  </div>
                  <span className="text-xs font-bold text-indigo-200">Evaluating Knowledge Depth...</span>
                </div>

                <div className="z-10 bg-slate-950/90 p-3 rounded-xl border border-slate-800 space-y-1">
                  <div className="text-[10px] font-bold text-indigo-400 uppercase tracking-wider">
                    Moderate Technical Probe #{activeQuestionIdx + 1}
                  </div>
                  <p className="text-xs text-slate-200 font-medium leading-snug">
                    "{currentQuestion.question}"
                  </p>
                </div>
              </div>
            </div>

            {/* Bottom Controls & Navigation */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 border-t border-slate-800">
              <div className="flex items-center gap-2">
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={activeQuestionIdx === 0}
                  onClick={() => setActiveQuestionIdx((prev) => prev - 1)}
                  className="bg-slate-800 text-slate-300 border-slate-700 text-xs"
                >
                  ← Previous Probe
                </Button>
                <Button
                  size="sm"
                  variant="secondary"
                  disabled={activeQuestionIdx >= questions.length - 1}
                  onClick={() => setActiveQuestionIdx((prev) => prev + 1)}
                  className="bg-slate-800 text-slate-300 border-slate-700 text-xs"
                >
                  Next Moderate Probe →
                </Button>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  onClick={finishCall}
                  className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-5 shadow-lg shadow-emerald-600/20"
                >
                  ✓ Complete AI Sounding Board Evaluation
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* Evaluated Score Card View */}
        {callState === "evaluated" && (
          <div className="p-8 text-center space-y-6">
            <div className="w-20 h-20 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center mx-auto shadow-xl">
              <span className="text-3xl text-emerald-400 font-black">{simulatedScore}%</span>
            </div>

            <div className="max-w-md mx-auto space-y-2">
              <h3 className="text-xl font-bold font-display text-white">
                Proctored AI Knowledge Verification Complete
              </h3>
              <p className="text-xs text-slate-400 leading-relaxed">
                Candidate <strong className="text-white">{candidateName}</strong> successfully completed the 1-on-1 AI Video Sounding Board assessment with <strong className="text-emerald-400">91% Verified Technical Depth</strong>. No proctoring or anti-cheating anomalies were detected.
              </p>
            </div>

            <div className="pt-2 flex justify-center">
              <Button onClick={onClose} className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6">
                Return to Candidate Dashboard
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
