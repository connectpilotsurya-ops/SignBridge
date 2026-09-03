"use client";

import { useState } from "react";
import type { IntegrityReport } from "@/types/api";

export function PdfInspector({
  integrity,
  rawText,
  sanitizedText,
}: {
  integrity?: IntegrityReport;
  rawText?: string;
  sanitizedText?: string;
}) {
  const [viewMode, setViewMode] = useState<"clean" | "raw" | "diff">("clean");

  const score = integrity?.score ?? 100;
  const flags = integrity?.flags ?? [];

  return (
    <div className="bg-white rounded-2xl border border-border/80 p-5 shadow-sm space-y-5">
      {/* Header & Integrity Meter */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-border">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-lg">🛡️</span>
            <h3 className="font-display font-bold text-base text-ink-900">
              PDF Anti-Gaming Forensic Inspector
            </h3>
          </div>
          <p className="text-xs text-ink-500 mt-0.5">
            PyMuPDF run-level font size, color, & position analysis to filter keyword-stuffing hacks.
          </p>
        </div>

        <div className="flex items-center gap-3 bg-slate-50 p-2.5 rounded-xl border border-slate-200">
          <div className="text-right">
            <div className="text-[10px] font-bold text-ink-400 uppercase tracking-wider">Document Integrity</div>
            <div className={`text-lg font-black font-display ${score >= 90 ? "text-emerald-600" : score >= 70 ? "text-amber-600" : "text-rose-600"}`}>
              {score.toFixed(0)} / 100
            </div>
          </div>
          <div className={`w-3 h-10 rounded-full ${score >= 90 ? "bg-emerald-500" : score >= 70 ? "bg-amber-500" : "bg-rose-500"}`} />
        </div>
      </div>

      {/* Forensic Flags List */}
      {flags.length === 0 ? (
        <div className="flex items-center gap-2 p-3 bg-emerald-50 text-emerald-800 text-xs font-medium rounded-xl border border-emerald-200/60">
          <span>✅</span> No forensic anomalies detected. Document matches natural human formatting.
        </div>
      ) : (
        <div className="space-y-2">
          <div className="text-xs font-bold text-ink-700 uppercase tracking-wider">Detected Formatting Anomalies:</div>
          <div className="grid gap-2">
            {flags.map((flag, idx) => (
              <div
                key={idx}
                className="p-3 bg-rose-50/80 rounded-xl border border-rose-200/70 text-xs text-rose-900 flex items-start gap-2.5"
              >
                <span className="text-rose-600 font-bold shrink-0">⚠️</span>
                <div>
                  <span className="font-bold text-rose-950 uppercase text-[10px] bg-rose-200/60 px-1.5 py-0.5 rounded mr-1.5">
                    {flag.type.replace(/_/g, " ")}
                  </span>
                  <span>{flag.description}</span>
                  {flag.evidence_text && (
                    <div className="mt-1 font-mono text-[11px] bg-rose-100/70 p-1.5 rounded border border-rose-200 text-rose-800">
                      Flagged content: &quot;{flag.evidence_text}&quot;
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* View Mode Toggle Controls */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 bg-slate-100 p-1 rounded-xl">
          <button
            onClick={() => setViewMode("clean")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewMode === "clean" ? "bg-white text-primary shadow-xs" : "text-ink-500 hover:text-ink-900"
            }`}
          >
            Verified Evidence Text
          </button>
          <button
            onClick={() => setViewMode("raw")}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              viewMode === "raw" ? "bg-white text-primary shadow-xs" : "text-ink-500 hover:text-ink-900"
            }`}
          >
            Raw Document Layer
          </button>
        </div>

        <span className="text-[11px] text-ink-400 font-medium hidden sm:inline">
          {viewMode === "clean" ? "Excludes hidden/tiny text" : "Includes unprocessed PDF text runs"}
        </span>
      </div>

      {/* Text Content Inspector Box */}
      <div className="bg-slate-950 text-slate-200 p-4 rounded-xl font-mono text-xs overflow-x-auto max-h-60 scrollbar-thin border border-slate-800 leading-relaxed">
        {viewMode === "clean" ? (
          sanitizedText ? (
            <p className="whitespace-pre-wrap">{sanitizedText}</p>
          ) : (
            <p className="text-slate-500 italic">Sanitized evidence text preview active.</p>
          )
        ) : (
          rawText ? (
            <p className="whitespace-pre-wrap text-amber-200/90">{rawText}</p>
          ) : (
            <p className="text-slate-500 italic">Raw document layer preview active.</p>
          )
        )}
      </div>
    </div>
  );
}
