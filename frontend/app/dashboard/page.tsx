"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { JobSummary } from "@/types/api";
import { Button, Card, EmptyState, PageHeader, Pill, Spinner } from "@/components/ui";

export default function DashboardPage() {
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .get<JobSummary[]>("/api/jobs")
      .then(setJobs)
      .catch((e) => setError(e.message));
  }, []);

  const totalCandidates = jobs ? jobs.reduce((acc, j) => acc + j.candidate_count, 0) : 0;
  const totalReviews = jobs ? jobs.reduce((acc, j) => acc + j.review_required_count, 0) : 0;

  return (
    <div className="space-y-8">
      <PageHeader
        title="Candidate Evidence Dashboard"
        description="Rank candidates by verified sentence-level evidence. Anti-gaming forensic checks run automatically before scoring."
        actions={
          <Link href="/dashboard/jobs/new">
            <Button variant="primary" className="shadow-md shadow-primary/25">
              + Post New Job
            </Button>
          </Link>
        }
      />

      {/* Top Metrics Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="p-5 border-l-4 border-l-primary bg-white hover:shadow-md transition-shadow">
          <div className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Active Jobs</div>
          <div className="text-3xl font-extrabold text-ink-900 mt-2 font-display">
            {jobs ? jobs.length : "—"}
          </div>
          <div className="text-xs text-primary font-medium mt-1">Role pipelines open</div>
        </Card>

        <Card className="p-5 border-l-4 border-l-accent bg-white hover:shadow-md transition-shadow">
          <div className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Candidates Analyzed</div>
          <div className="text-3xl font-extrabold text-ink-900 mt-2 font-display">
            {jobs ? totalCandidates : "—"}
          </div>
          <div className="text-xs text-ink-500 mt-1">Pydantic evidence verified</div>
        </Card>

        <Card className="p-5 border-l-4 border-l-warning bg-white hover:shadow-md transition-shadow">
          <div className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Review Required</div>
          <div className="text-3xl font-extrabold text-amber-600 mt-2 font-display">
            {jobs ? totalReviews : "—"}
          </div>
          <div className="text-xs text-amber-700 font-medium mt-1">Forensic flags or gaps</div>
        </Card>

        <Card className="p-5 border-l-4 border-l-emerald-500 bg-white hover:shadow-md transition-shadow">
          <div className="text-xs font-semibold text-ink-400 uppercase tracking-wider">Deterministic Engine</div>
          <div className="text-3xl font-extrabold text-emerald-600 mt-2 font-display">
            100%
          </div>
          <div className="text-xs text-emerald-700 font-medium mt-1">Audit-proof Python rules</div>
        </Card>
      </div>

      {error && <p className="text-sm text-danger mb-4">{error}</p>}

      {!jobs && !error && (
        <div className="flex justify-center py-20 text-ink-400">
          <Spinner className="w-8 h-8 text-primary" />
        </div>
      )}

      {jobs && jobs.length === 0 && (
        <Card className="p-8">
          <EmptyState
            title="No hiring pipelines active"
            description="Create your first job to paste in a description, extract requirements, and evaluate candidates against evidence."
            action={
              <Link href="/dashboard/jobs/new">
                <Button variant="primary">+ Create First Job</Button>
              </Link>
            }
          />
        </Card>
      )}

      {jobs && jobs.length > 0 && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-bold font-display text-ink-900">Active Role Pipelines</h2>
            <span className="text-xs text-ink-400 font-medium">Sorted by recent activity</span>
          </div>

          <div className="grid gap-4">
            {jobs.map((job) => (
              <Card
                key={job.id}
                className="p-6 bg-white hover:border-primary/50 transition-all hover:shadow-md group"
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-6">
                  <div className="space-y-2 min-w-0 flex-1">
                    <div className="flex items-center gap-3">
                      <Link href={`/dashboard/jobs/${job.id}`}>
                        <h3 className="font-display font-bold text-xl text-ink-900 group-hover:text-primary transition-colors">
                          {job.title}
                        </h3>
                      </Link>
                      {job.review_required_count > 0 && (
                        <Pill tone="warning">{job.review_required_count} Needs Recruiter Review</Pill>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-4 text-xs text-ink-500 font-medium">
                      <span className="inline-flex items-center gap-1.5 bg-slate-100 px-2.5 py-1 rounded-md text-ink-700">
                        👥 {job.candidate_count} Candidates Ranked
                      </span>
                      {job.top_candidate_score !== null && (
                        <span className="inline-flex items-center gap-1.5 bg-primary-soft text-primary px-2.5 py-1 rounded-md font-semibold">
                          ⭐ Top Match Score: {job.top_candidate_score.toFixed(1)} / 100
                        </span>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <Link href={`/dashboard/jobs/${job.id}/ranking`}>
                      <Button variant="primary" size="md" className="shadow-sm shadow-primary/20">
                        View AI Ranking →
                      </Button>
                    </Link>
                    <Link href={`/dashboard/jobs/${job.id}`}>
                      <Button variant="secondary" size="md">
                        Manage Job
                      </Button>
                    </Link>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
