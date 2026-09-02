"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { CandidateRow, JobOut } from "@/types/api";
import {
  Button,
  Card,
  CandidateStatusBadge,
  EmptyState,
  PageHeader,
  Pill,
  Spinner,
} from "@/components/ui";

export default function JobDetailPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const [job, setJob] = useState<JobOut | null>(null);
  const [candidates, setCandidates] = useState<CandidateRow[] | null>(null);
  const [blindMode, setBlindMode] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [uploadErrors, setUploadErrors] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const loadJob = useCallback(() => {
    api
      .get<JobOut>(`/api/jobs/${jobId}`)
      .then(setJob)
      .catch((e) => setError(e.message));
  }, [jobId]);

  const loadCandidates = useCallback(() => {
    api
      .get<CandidateRow[]>(`/api/jobs/${jobId}/candidates?blind=${blindMode}`)
      .then(setCandidates)
      .catch((e) => setError(e.message));
  }, [jobId, blindMode]);

  useEffect(() => {
    loadJob();
  }, [loadJob]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

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

  async function handleUpload(files: FileList | null) {
    if (!files || files.length === 0) return;
    setUploading(true);
    setUploadErrors([]);
    const form = new FormData();
    form.append("job_id", jobId);
    Array.from(files).forEach((f) => form.append("files", f));
    try {
      const result = await api.postForm<{ results: { file_name: string; application_id?: string; error?: string }[] }>(
        "/api/resumes/upload",
        form
      );
      const failures = result.results.filter((r) => r.error).map((r) => `${r.file_name}: ${r.error}`);
      setUploadErrors(failures);
      loadCandidates();
      loadJob();
    } catch (err) {
      setUploadErrors([err instanceof ApiError ? err.message : "Upload failed."]);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  if (!job) {
    return (
      <div className="flex justify-center py-20 text-ink-400">
        <Spinner className="w-6 h-6" />
      </div>
    );
  }

  return (
    <div>
      <PageHeader
        title={job.title}
        description={[job.department, job.location, job.experience_requirement].filter(Boolean).join(" · ")}
      />

      {error && <p className="text-sm text-danger mb-4">{error}</p>}

      <Card className="p-6 mb-6">
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

      {job.requirements_analyzed && (
        <Card className="p-6 mb-6">
          <h2 className="font-display font-semibold text-ink-900 mb-1">Upload resumes</h2>
          <p className="text-sm text-ink-500 mb-4">
            PDF only. Each resume is parsed, checked for manipulation, and scored against the
            requirements above — synchronously, so results appear as soon as this finishes.
          </p>
          <div className="flex items-center gap-3">
            <input
              ref={fileInputRef}
              type="file"
              accept="application/pdf"
              multiple
              disabled={uploading}
              onChange={(e) => handleUpload(e.target.files)}
              className="text-sm text-ink-500 file:mr-3 file:rounded-xl file:border-0 file:bg-primary-soft file:text-primary file:px-3.5 file:py-2 file:text-sm file:font-medium hover:file:bg-primary/20"
            />
            {uploading && <Spinner className="w-4 h-4 text-primary" />}
          </div>
          {uploadErrors.length > 0 && (
            <ul className="mt-3 text-sm text-danger space-y-1">
              {uploadErrors.map((e, i) => (
                <li key={i}>{e}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      <div className="flex items-center justify-between mb-3">
        <h2 className="font-display font-semibold text-ink-900">Candidates</h2>
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
          <EmptyState title="No candidates yet" description="Upload resumes above to start analysis." />
        </Card>
      )}

      {candidates && candidates.length > 0 && (
        <div className="grid gap-3">
          {candidates.map((c) => (
            <Link key={c.application_id} href={`/dashboard/jobs/${jobId}/candidates/${c.application_id}`}>
              <Card className="p-5 hover:border-primary/40 transition-colors cursor-pointer">
                <div className="flex items-center justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-display font-semibold text-ink-900">{c.display_label}</h3>
                      <CandidateStatusBadge status={c.status} />
                    </div>
                    <div className="flex items-center gap-4 text-sm text-ink-500 mt-1.5">
                      <span>Match {c.match_score.toFixed(0)}</span>
                      <span>Evidence {c.evidence_confidence.toFixed(0)}</span>
                      <span>Integrity {c.document_integrity.toFixed(0)}</span>
                    </div>
                    {(c.top_strengths?.length || c.major_gaps?.length) && (
                      <div className="flex flex-wrap gap-1.5 mt-2.5">
                        {c.top_strengths?.map((s) => (
                          <Pill key={`s-${s}`} tone="success">
                            {s}
                          </Pill>
                        ))}
                        {c.major_gaps?.map((g) => (
                          <Pill key={`g-${g}`} tone="danger">
                            {g}
                          </Pill>
                        ))}
                      </div>
                    )}
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
