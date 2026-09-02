"use client";

import { useAuth } from "@/lib/auth-context";
import { API_BASE_URL } from "@/lib/api";
import { Card, PageHeader, Pill } from "@/components/ui";

export default function SettingsPage() {
  const { session } = useAuth();

  return (
    <div className="max-w-2xl">
      <PageHeader title="Settings" description="Organization, account, and how this instance is running." />

      <Card className="p-6 mb-6">
        <h2 className="font-display font-semibold text-ink-900 mb-4">Organization</h2>
        <dl className="space-y-3 text-sm">
          <div className="flex justify-between">
            <dt className="text-ink-500">Organization</dt>
            <dd className="font-medium text-ink-900">{session?.organizationName}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-500">Signed in as</dt>
            <dd className="font-medium text-ink-900">{session?.email}</dd>
          </div>
          <div className="flex justify-between">
            <dt className="text-ink-500">API endpoint</dt>
            <dd className="font-mono text-xs text-ink-500">{API_BASE_URL}</dd>
          </div>
        </dl>
      </Card>

      <Card className="p-6 mb-6">
        <h2 className="font-display font-semibold text-ink-900 mb-2">Blind review mode</h2>
        <p className="text-sm text-ink-500 leading-relaxed">
          Spec §30: blind mode hides a candidate&rsquo;s name behind a label like{" "}
          <Pill tone="neutral">Candidate #002</Pill> everywhere it&rsquo;s shown — the underlying
          record and every score are completely unaffected. It&rsquo;s a per-view toggle rather than
          an org-wide switch: turn it on from the candidate list on any job page when you want to
          review evidence before seeing who it belongs to.
        </p>
      </Card>

      <Card className="p-6">
        <h2 className="font-display font-semibold text-ink-900 mb-2">Analysis mode</h2>
        <p className="text-sm text-ink-500 leading-relaxed">
          This instance is running in demo mode: JD/resume interpretation uses a deterministic,
          zero-dependency mock reasoner instead of a live Gemini call, and vector search runs
          in-memory instead of against Qdrant. Every analysis response is labeled with which mode
          produced it — nothing is silently blurred between the two. Supplying real credentials in
          the backend&rsquo;s environment switches every adapter to the real stack with no code
          changes.
        </p>
      </Card>
    </div>
  );
}
