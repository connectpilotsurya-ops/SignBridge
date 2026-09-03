"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CandidateSummary, JobOut } from "@/types/api";
import {
  Button,
  Card,
  CandidateStatusBadge,
  EmptyState,
  IntegrityBadge,
  PageHeader,
  Pill,
  ScoreGauge,
  Spinner,
} from "@/components/ui";

interface FileBatchStatus {
  fileName: string;
  sizeBytes: number;
  status: "queued" | "uploading" | "analyzing" | "completed" | "error";
  applicationId?: string;
  error?: string;
}

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobOut | null>(null);
  const [candidates, setCandidates] = useState<CandidateSummary[] | null>(null);
  const [blindMode, setBlindMode] = useState(false);

  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fileBatch, setFileBatch] = useState<FileBatchStatus[]>([]);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function loadJob() {
    api
      .get<JobOut>(`/api/jobs/${jobId}`)
      .then((data) => setJob(data))
      .catch((err) => setError(err.message));
  }

  function loadCandidates() {
    api
      .get<CandidateSummary[]>(`/api/jobs/${jobId}/candidates?blind=${blindMode}`)
      .then((data) => setCandidates(data))
      .catch((err) => setError(err.message));
  }

  useEffect(() => {
    loadJob();
  }, [jobId]);

  useEffect(() => {
    loadCandidates();
  }, [jobId, blindMode]);

  async function handleAnalyze() {
    setAnalyzing(true);
    setError(null);
    try {
      const updated = await api.post<JobOut>(`/api/jobs/${jobId}/analyze`);
      setJob(updated);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not analyze requirements.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleBatchUpload(filesList: FileList | null) {
    if (!filesList || filesList.length === 0) return;
    const filesArr = Array.from(filesList);

    // Initialize batch file status queue
    const batchQueue: FileBatchStatus[] = filesArr.map((f) => ({
      fileName: f.name,
      sizeBytes: f.size,
      status: "queued",
    }));
    setFileBatch(batchQueue);
    setUploading(true);

    const form = new FormData();
    form.append("job_id", jobId);
    filesArr.forEach((f) => form.append("files", f));

    try {
      // Mark as uploading/analyzing
      setFileBatch((prev) => prev.map((item) => ({ ...item, status: "analyzing" })));

      const response = await api.postForm<{
        results: { file_name: string; application_id?: string; error?: string }[];
      }>("/api/resumes/upload", form);

      // Update individual file status based on separate analysis outcome
      setFileBatch((prev) =>
        prev.map((item) => {
          const res = response.results.find((r) => r.file_name === item.fileName);
          if (res?.error) {
            return { ...item, status: "error", error: res.error };
          }
          return {
            ...item,
            status: "completed",
            applicationId: res?.application_id,
          };
        })
      );

      loadCandidates();
      loadJob();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Batch upload failed.");
      setFileBatch((prev) => prev.map((item) => ({ ...item, status: "error", error: "Upload failed" })));
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (!job) {
    return (
      <div className="flex justify-center py-20 text-ink-400">
        <Spinner className="w-6 h-6 text-primary" />
      </div>
    );
  }

  return (
    <div className="max-w-4xl space-y-6">
      <PageHeader
        title={job.title}
        description={[job.department, job.location, job.experience_requirement].filter(Boolean).join(" · ")}
      />

      {error && <p className="text-sm text-danger">{error}</p>}

      {/* Requirements Section */}
      <Card className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-display font-semibold text-ink-900">Requirements</h2>
          {!job.requirements_analyzed && (
            <Button onClick={handleAnalyze} disabled={analyzing} size="sm">
              {analyzing ? "Analyzing…" : "Analyze requirements"}
            </Button>
          )}
        </div>

        {!job.requirements_analyzed && (
          <p className="text-sm text-ink-500">
            Requirements haven&rsquo;t been extracted from this job description yet. Run analysis
            before uploading resumes — matching needs to know what to look for.
          </p>
        )}

        {job.requirements_analyzed && (
          <div className="flex flex-wrap gap-2">
            {job.requirements.map((req) => (
              <Pill key={req.name} tone={req.importance === "must_have" ? "primary" : "neutral"}>
                {req.name}
                <span className="opacity-60">· {req.importance === "must_have" ? "must-have" : "preferred"}</span>
              </Pill>
            ))}
            {job.experience_years_min !== null && (
              <Pill tone="accent">{job.experience_years_min}+ years experience</Pill>
            )}
          </div>
        )}
      </Card>

      {/* Multi-Resume Batch Upload Card */}
      {job.requirements_analyzed && (
        <Card className="p-6">
          <div className="flex items-center justify-between mb-2">
            <h2 className="font-display font-semibold text-ink-900 flex items-center gap-2">
              <span>📁</span> Multi-Resume Batch Upload
            </h2>
            <span className="text-xs font-bold text-primary bg-primary-soft px-2.5 py-1 rounded-full">
              Multiple PDF Upload Enabled
            </span>
          </div>
          <p className="text-xs text-ink-500 mb-4">
            Select or drag & drop multiple PDF resumes at once. Each resume is parsed, checked for white-text manipulation, and analyzed **separately** into an isolated candidate profile.
          </p>

          {/* Upload Input & Dropzone styling */}
          <div className="p-6 border-2 border-dashed border-primary/30 hover:border-primary rounded-2xl bg-indigo-50/20 flex flex-col items-center justify-center text-center transition-all">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              multiple
              disabled={uploading}
              onChange={(e) => handleBatchUpload(e.target.files)}
              className="hidden"
              id="multi-resume-input"
            />
            <label
              htmlFor="multi-resume-input"
              className="cursor-pointer flex flex-col items-center space-y-2 group"
            >
              <div className="w-12 h-12 rounded-2xl bg-primary-soft flex items-center justify-center text-primary group-hover:scale-105 transition-transform">
                <span className="text-xl">📄</span>
              </div>
              <span className="font-bold text-sm text-ink-900">
                Choose Multiple PDF Resumes or Drag & Drop
              </span>
              <span className="text-xs text-ink-400">
                Hold Ctrl / Cmd to select multiple files at once
              </span>
            </label>
          </div>

          {/* Active Batch Processing Status List */}
          {fileBatch.length > 0 && (
            <div className="mt-5 space-y-2 pt-4 border-t border-border">
              <div className="text-xs font-bold text-ink-700 uppercase tracking-wider flex items-center justify-between">
                <span>Batch Upload Queue ({fileBatch.length} Resumes)</span>
                {uploading && (
                  <span className="flex items-center gap-1.5 text-primary text-xs font-semibold">
                    <Spinner className="w-3.5 h-3.5" /> Analyzing separately...
                  </span>
                )}
              </div>

              <div className="grid gap-2">
                {fileBatch.map((f, idx) => (
                  <div
                    key={idx}
                    className="p-3 bg-slate-50 rounded-xl border border-slate-200 flex items-center justify-between gap-3 text-xs"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="text-base">📄</span>
                      <span className="font-semibold text-ink-900 truncate">
                        {f.fileName}
                      </span>
                      <span className="text-ink-400 text-[10px]">
                        ({(f.sizeBytes / 1024).toFixed(0)} KB)
                      </span>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {f.status === "analyzing" && (
                        <span className="text-amber-600 font-bold flex items-center gap-1">
                          <Spinner className="w-3 h-3 text-amber-600" /> Analyzing
                        </span>
                      )}
                      {f.status === "completed" && (
                        <span className="text-emerald-600 font-bold">
                          ✓ Separate Analysis Ready
                        </span>
                      )}
                      {f.status === "error" && (
                        <span className="text-rose-600 font-bold">
                          ✕ {f.error || "Failed"}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Candidate List Header & Blind Mode */}
      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display font-semibold text-ink-900">
          Analyzed Candidates Pool ({candidates?.length || 0})
        </h2>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-ink-500 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={blindMode}
              onChange={(e) => setBlindMode(e.target.checked)}
              className="rounded border-border-strong text-primary focus:ring-primary/30"
            />
            Blind review mode
          </label>
          <Link
            href={`/dashboard/jobs/${jobId}/ranking`}
            className="text-sm font-medium text-accent hover:text-accent-hover transition-colors"
          >
            View full AI ranking →
          </Link>
        </div>
      </div>

      {candidates && candidates.length === 0 && (
        <Card>
          <EmptyState title="No candidates analyzed yet" description="Upload multiple resumes above to begin separate candidate analysis." />
        </Card>
      )}

      {/* Individual Candidate Analysis Cards */}
      {candidates && candidates.length > 0 && (
        <div className="grid gap-3">
          {candidates.map((c) => (
            <Link key={c.application_id} href={`/dashboard/jobs/${jobId}/candidates/${c.application_id}`}>
              <Card className="p-5 hover:border-primary/40 transition-colors cursor-pointer">
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-display font-semibold text-ink-900 text-base truncate">
                        {c.display_label}
                      </h3>
                      <CandidateStatusBadge status={c.status} />
                    </div>
                    <div className="flex items-center gap-3 mt-2 text-xs text-ink-500">
                      <span>Integrity:</span>
                      <IntegrityBadge category={c.integrity_category || "normal"} />
                      <span>·</span>
                      <span>Confidence: {(c.evidence_confidence * 100).toFixed(0)}%</span>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 shrink-0">
                    <div className="text-right">
                      <div className="text-xs text-ink-400 mb-0.5">Match Score</div>
                      <ScoreGauge score={c.match_score} size={64} />
                    </div>
                  </div>
                </div>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
