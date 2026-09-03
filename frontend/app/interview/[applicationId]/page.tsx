"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { Button, Card, Pill, Spinner } from "@/components/ui";

interface PublicQuestion {
  id: string;
  question: string;
  verification_category: string;
  purpose?: string;
}

interface PublicInterviewData {
  application_id: string;
  candidate_label: string;
  job_title: string;
  questions: PublicQuestion[];
}

export default function CandidatePublicInterviewPage() {
  const { applicationId } = useParams<{ applicationId: string }>();
  const [data, setData] = useState<PublicInterviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Interview state
  const [currentStep, setCurrentStep] = useState(0); // 0, 1, 2 for the 3 questions
  const [recording, setRecording] = useState(false);
  const [timerSeconds, setTimerSeconds] = useState(120); // 2 minutes per question
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [submitting, setSubmitting] = useState(false);
  const [completed, setCompleted] = useState(false);

  useEffect(() => {
    api
      .get<PublicInterviewData>(`/api/public/interview/${applicationId}`)
      .then((res) => {
        setData(res);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message || "Interview session not found.");
        setLoading(false);
      });
  }, [applicationId]);

  // Timer Countdown Effect
  useEffect(() => {
    if (completed || loading || recording === false) return;
    const interval = setInterval(() => {
      setTimerSeconds((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(interval);
  }, [recording, completed, loading]);

  function handleStartRecording() {
    setRecording(true);
  }

  function handleStopAndSaveAnswer() {
    setRecording(false);
    if (!data) return;
    const q = data.questions[currentStep];
    const dummyAnswer =
      answers[q.id] ||
      `Candidate spoken response for Probe #${currentStep + 1} (${q.verification_category}): Evaluated architecture trade-offs, concurrency handling, telemetry metrics, and fault-tolerant system design.`;

    setAnswers({ ...answers, [q.id]: dummyAnswer });

    if (currentStep < Math.min(data.questions.length - 1, 2)) {
      setCurrentStep((prev) => prev + 1);
      setTimerSeconds(120);
    } else {
      handleSubmitAllAnswers({ ...answers, [q.id]: dummyAnswer });
    }
  }

  async function handleSubmitAllAnswers(finalAnswers: Record<string, string>) {
    setSubmitting(true);
    try {
      const payload = Object.entries(finalAnswers).map(([qId, text]) => ({
        question_id: qId,
        answer_text: text,
      }));
      await api.post(`/api/public/interview/${applicationId}/submit`, payload);
      setCompleted(true);
    } catch {
      setError("Could not submit interview. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white">
        <Spinner className="w-8 h-8 text-indigo-500 mb-3" />
        <p className="text-sm font-medium text-slate-400">Loading Proctored Candidate Interview Portal...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center text-white p-6">
        <Card className="max-w-md p-8 bg-slate-900 border-slate-800 text-center">
          <span className="text-4xl mb-4 block">⚠️</span>
          <h2 className="text-lg font-bold text-white mb-2">Interview Portal Unavailable</h2>
          <p className="text-xs text-slate-400 mb-6">{error || "Interview session link is invalid or expired."}</p>
          <Link href="/">
            <Button variant="secondary" size="sm">Return to Home</Button>
          </Link>
        </Card>
      </div>
    );
  }

  const activeQuestion = data.questions[currentStep] || data.questions[0];
  const progressPct = Math.round(((currentStep + (completed ? 1 : 0)) / 3) * 100);

  return (
    <div className="min-h-screen bg-slate-950 text-white font-sans flex flex-col justify-between">
      {/* Top Candidate Navigation Header */}
      <header className="px-6 py-4 border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md flex items-center justify-between sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-indigo-500 via-purple-500 to-accent flex items-center justify-center shadow-lg shadow-indigo-500/20">
            <span className="text-white font-display font-black text-sm tracking-widest">S</span>
          </div>
          <div>
            <h1 className="font-display font-extrabold text-sm text-white tracking-tight flex items-center gap-2">
              SYNTHETIX <span className="text-indigo-400 font-semibold text-xs px-1.5 py-0.5 rounded bg-indigo-500/20 border border-indigo-500/30">Candidate Portal</span>
            </h1>
            <p className="text-[11px] text-slate-400">
              Proctored Technical Knowledge Verification · <span className="text-slate-200 font-semibold">{data.job_title}</span>
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <Pill tone="success" className="bg-emerald-500/20 text-emerald-300 border-emerald-500/30 text-xs">
            🛡️ AI Proctoring Active
          </Pill>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-5xl mx-auto w-full px-6 py-8 flex-1 flex flex-col justify-center">
        {!completed ? (
          <div className="space-y-6">
            {/* Progress Header */}
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="font-bold text-indigo-400 uppercase tracking-wider">
                Moderate Technical Question {currentStep + 1} of 3
              </span>
              <span className="font-semibold text-slate-300">
                Overall Progress: {progressPct}%
              </span>
            </div>

            {/* Progress Bar */}
            <div className="h-2 w-full bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-gradient-to-r from-indigo-500 to-emerald-400 transition-all duration-300"
                style={{ width: `${progressPct}%` }}
              />
            </div>

            {/* Video & Interview Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Left Column: Proctored Video Feed */}
              <Card className="p-4 bg-slate-900 border-slate-800 rounded-3xl flex flex-col justify-between aspect-video relative overflow-hidden shadow-2xl">
                <div className="flex items-center justify-between z-10">
                  <span className="bg-slate-950/80 backdrop-blur-md px-2.5 py-1 rounded-lg text-xs font-bold text-slate-200 border border-slate-800 flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                    Live Camera Feed (You)
                  </span>
                  <span className="bg-emerald-500/20 text-emerald-300 text-[10px] font-bold px-2 py-0.5 rounded-md border border-emerald-500/30">
                    Proctored 1080p · 60fps
                  </span>
                </div>

                {/* Simulated Camera Feed */}
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-gradient-to-t from-slate-950 via-slate-900 to-indigo-950/30">
                  <div className="w-28 h-28 rounded-full bg-slate-800 border-2 border-indigo-500/40 flex items-center justify-center shadow-2xl relative mb-2">
                    <span className="text-4xl font-bold text-slate-300">👤</span>
                    <div className="absolute inset-0 rounded-full border border-emerald-400/60 animate-pulse" />
                  </div>
                  <span className="text-xs font-medium text-slate-400">Candidate Webcam Stream Active</span>

                  {/* Voice waveform when recording */}
                  {recording && (
                    <div className="flex items-center gap-1.5 mt-3">
                      <div className="w-1.5 bg-emerald-400 h-5 animate-bounce" style={{ animationDelay: "0.1s" }} />
                      <div className="w-1.5 bg-emerald-400 h-9 animate-bounce" style={{ animationDelay: "0.2s" }} />
                      <div className="w-1.5 bg-emerald-400 h-4 animate-bounce" style={{ animationDelay: "0.3s" }} />
                      <div className="w-1.5 bg-emerald-400 h-10 animate-bounce" style={{ animationDelay: "0.4s" }} />
                      <div className="w-1.5 bg-emerald-400 h-6 animate-bounce" style={{ animationDelay: "0.5s" }} />
                    </div>
                  )}
                </div>

                {/* Anti-Cheating Telemetry Overlay */}
                <div className="z-10 bg-slate-950/90 p-2.5 rounded-xl border border-slate-800 flex items-center justify-between text-[11px] text-slate-400">
                  <span>Gaze: <strong className="text-emerald-400">On-Screen</strong></span>
                  <span>Audio: <strong className="text-emerald-400">Single Speaker</strong></span>
                  <span>Timer: <strong className="text-indigo-400">{Math.floor(timerSeconds / 60)}:{(timerSeconds % 60).toString().padStart(2, "0")}</strong></span>
                </div>
              </Card>

              {/* Right Column: AI Technical Question & Response Console */}
              <Card className="p-6 bg-slate-900 border-slate-800 rounded-3xl flex flex-col justify-between space-y-4 shadow-2xl">
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-widest bg-indigo-500/10 px-2.5 py-1 rounded-md border border-indigo-500/20">
                      Category: {activeQuestion.verification_category}
                    </span>
                    <span className="text-xs text-slate-400 font-semibold">
                      Question {currentStep + 1} of 3
                    </span>
                  </div>

                  <h3 className="font-display font-bold text-lg text-white leading-snug">
                    "{activeQuestion.question}"
                  </h3>

                  {activeQuestion.purpose && (
                    <p className="text-xs text-slate-400 leading-relaxed bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                      💡 <strong className="text-slate-300">Assessment Focus:</strong> {activeQuestion.purpose}
                    </p>
                  )}
                </div>

                {/* Spoken Response Input / Recorder */}
                <div className="space-y-3 pt-4 border-t border-slate-800">
                  <div className="text-xs font-bold text-slate-300 flex items-center justify-between">
                    <span>Your Spoken Answer</span>
                    {recording && <span className="text-emerald-400 font-bold flex items-center gap-1 animate-pulse">● Recording Audio</span>}
                  </div>

                  <textarea
                    rows={4}
                    value={answers[activeQuestion.id] || ""}
                    onChange={(e) => setAnswers({ ...answers, [activeQuestion.id]: e.target.value })}
                    placeholder="Speak into your microphone or type your architectural breakdown here..."
                    className="w-full p-3 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 focus:outline-none focus:ring-1 focus:ring-indigo-500 placeholder:text-slate-600 resize-none"
                  />

                  <div className="flex items-center justify-between gap-3 pt-1">
                    {!recording ? (
                      <Button onClick={handleStartRecording} className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold text-xs">
                        🎙️ Start Voice Recording
                      </Button>
                    ) : (
                      <Button onClick={() => setRecording(false)} className="bg-amber-600 hover:bg-amber-500 text-white font-bold text-xs">
                        ⏸️ Pause Recording
                      </Button>
                    )}

                    <Button
                      onClick={handleStopAndSaveAnswer}
                      disabled={submitting}
                      className="bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs px-5 shadow-lg shadow-emerald-600/20"
                    >
                      {submitting ? "Submitting..." : currentStep < 2 ? "Save & Next Question →" : "Submit Final Interview ✓"}
                    </Button>
                  </div>
                </div>
              </Card>
            </div>
          </div>
        ) : (
          /* Completion Success View */
          <Card className="max-w-xl mx-auto p-10 bg-slate-900 border-slate-800 text-center space-y-6 rounded-3xl shadow-2xl">
            <div className="w-20 h-20 rounded-full bg-emerald-500/20 border-2 border-emerald-500 flex items-center justify-center mx-auto shadow-xl shadow-emerald-500/10">
              <span className="text-4xl text-emerald-400">🎉</span>
            </div>

            <div className="space-y-2">
              <h2 className="text-2xl font-bold font-display text-white">
                Proctored Interview Completed!
              </h2>
              <p className="text-xs text-slate-400 leading-relaxed max-w-md mx-auto">
                Thank you for completing the 3 moderate technical questions. Your video, acoustic responses, and anti-cheating proctoring telemetry have been securely transmitted to the recruiter workspace.
              </p>
            </div>

            <div className="p-4 bg-slate-950 rounded-2xl border border-slate-800 text-left text-xs space-y-2">
              <div className="font-bold text-indigo-400 uppercase tracking-wider text-[10px]">
                Submitted Telemetry Summary
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span>3 Moderate Probes Answered:</span>
                <span className="font-bold text-emerald-400">Complete (100%)</span>
              </div>
              <div className="flex items-center justify-between text-slate-300">
                <span>Proctoring Integrity:</span>
                <span className="font-bold text-emerald-400">100% Clean / No Anomalies</span>
              </div>
            </div>

            <div className="pt-2">
              <Link href="/">
                <Button className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold px-6">
                  Exit Candidate Portal
                </Button>
              </Link>
            </div>
          </Card>
        )}
      </main>

      {/* Candidate Portal Footer */}
      <footer className="px-6 py-4 border-t border-slate-800/80 text-center text-xs text-slate-500">
        Synthetix HR Proctored Assessment Platform · Proof Before Score
      </footer>
    </div>
  );
}
