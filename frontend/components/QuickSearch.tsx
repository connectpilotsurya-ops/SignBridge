"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { JobSummary } from "@/types/api";

export function QuickSearch() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [jobs, setJobs] = useState<JobSummary[]>([]);
  const router = useRouter();

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape") setOpen(false);
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    if (open && jobs.length === 0) {
      api.get<JobSummary[]>("/api/jobs").then(setJobs).catch(() => {});
    }
  }, [open, jobs.length]);

  const filteredJobs = jobs.filter((j) =>
    j.title.toLowerCase().includes(query.toLowerCase())
  );

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-start justify-center pt-20 px-4 animate-in fade-in duration-150">
      <div className="bg-white w-full max-w-xl rounded-2xl shadow-2xl border border-slate-200 overflow-hidden space-y-0">
        {/* Search Input Bar */}
        <div className="flex items-center gap-3 px-4 py-3.5 border-b border-slate-200">
          <span className="text-slate-400 text-base">🔍</span>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Quick search jobs, candidate pipelines, or requirements... (ESC to close)"
            className="w-full text-sm font-medium text-ink-900 placeholder:text-ink-400 focus:outline-none bg-transparent"
            autoFocus
          />
          <kbd className="px-2 py-0.5 text-[10px] font-bold text-slate-400 bg-slate-100 rounded border border-slate-200">
            ESC
          </kbd>
        </div>

        {/* Results List */}
        <div className="max-h-80 overflow-y-auto p-2 scrollbar-thin">
          <div className="text-[10px] font-bold text-ink-400 uppercase tracking-wider px-3 py-1.5">
            Active Role Pipelines ({filteredJobs.length})
          </div>
          {filteredJobs.length === 0 ? (
            <div className="p-6 text-center text-xs text-ink-400">No matching pipelines found.</div>
          ) : (
            filteredJobs.map((job) => (
              <button
                key={job.id}
                onClick={() => {
                  setOpen(false);
                  router.push(`/dashboard/jobs/${job.id}/ranking`);
                }}
                className="w-full text-left p-3 rounded-xl hover:bg-primary-soft transition-colors flex items-center justify-between group"
              >
                <div>
                  <div className="font-bold text-sm text-ink-900 group-hover:text-primary transition-colors">
                    {job.title}
                  </div>
                  <div className="text-xs text-ink-400">
                    {job.candidate_count} Candidates Ranked · {job.review_required_count} Review Required
                  </div>
                </div>
                <span className="text-xs font-semibold text-primary opacity-0 group-hover:opacity-100 transition-opacity">
                  View Ranking →
                </span>
              </button>
            ))
          )}
        </div>

        <div className="p-2.5 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-[11px] text-ink-400 font-medium px-4">
          <span>Tip: Use ↑ ↓ keys to navigate, ENTER to select</span>
          <span className="text-primary">SYNTHETIX HR Quick Command</span>
        </div>
      </div>
    </div>
  );
}
