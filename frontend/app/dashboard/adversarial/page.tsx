"use client";

import { useRef, useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { AdversarialSuiteResult } from "@/types/api";
import { Button, Card, PageHeader, Pill, Spinner } from "@/components/ui";

function impactTone(impact: string): "success" | "warning" | "danger" | "neutral" {
  if (impact === "EXCLUDED") return "success";
  if (impact.startsWith("FLAGGED")) return "warning";
  if (impact.startsWith("INCLUDED")) return "danger";
  return "neutral";
}

export default function AdversarialSimulatorPage() {
  const [result, setResult] = useState<AdversarialSuiteResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function runSuite() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const file = fileInputRef.current?.files?.[0];
      let res: AdversarialSuiteResult;
      if (file) {
        const form = new FormData();
        form.append("file", file);
        res = await api.postForm<AdversarialSuiteResult>("/api/adversarial/test", form);
      } else {
        // No file selected -> call with no body at all rather than an
        // empty FormData, which some servers reject as a malformed
        // multipart payload.
        res = await api.post<AdversarialSuiteResult>("/api/adversarial/test");
      }
      setResult(res);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not run the adversarial suite.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="Adversarial resume simulator"
        description="Spec §29: takes a resume and produces six real, gamed variants — hidden text, tiny fonts, footer stuffing, repeated keywords, skills-only padding, and a hidden section — then runs the exact same parser and integrity detector used on every real upload. Nothing here is a canned demo result."
      />

      <Card className="p-6 mb-6">
        <div className="flex items-center gap-3">
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            className="text-sm text-ink-500 file:mr-3 file:rounded-xl file:border-0 file:bg-primary-soft file:text-primary file:px-3.5 file:py-2 file:text-sm file:font-medium hover:file:bg-primary/20"
          />
          <Button onClick={runSuite} disabled={loading}>
            {loading ? "Running…" : "Run attack suite"}
          </Button>
        </div>
        <p className="text-xs text-ink-400 mt-2">
          Leave the file empty to use a bundled, genuinely clean sample resume — no setup required.
        </p>
      </Card>

      {error && <p className="text-sm text-danger mb-4">{error}</p>}
      {loading && (
        <div className="flex justify-center py-16 text-ink-400">
          <Spinner className="w-6 h-6" />
        </div>
      )}

      {result && (
        <>
          <Card className="p-5 mb-4 flex items-center gap-6">
            <div>
              <div className="text-2xl font-display font-bold text-ink-900">
                {result.summary.detected}/{result.summary.total_attacks}
              </div>
              <div className="text-xs text-ink-500">attacks detected</div>
            </div>
            <div>
              <div className="text-2xl font-display font-bold text-ink-900">
                {result.summary.excluded_from_matching}
              </div>
              <div className="text-xs text-ink-500">terms excluded from matching</div>
            </div>
            <div className="text-xs text-ink-400 ml-auto">Source: {result.source}</div>
          </Card>

          <div className="space-y-3">
            {result.attacks.map((atk) => (
              <Card key={atk.attack_type} className="p-5">
                <div className="flex items-center justify-between gap-3 mb-2">
                  <h3 className="font-display font-semibold text-ink-900">{atk.label}</h3>
                  <Pill tone={atk.detected ? "success" : "danger"}>
                    {atk.detected ? "Detected" : "Undetected"}
                  </Pill>
                </div>
                <div className="flex flex-wrap gap-2 mb-2">
                  <Pill tone={impactTone(atk.matching_impact)}>{atk.matching_impact}</Pill>
                  <Pill tone={atk.integrity_impact === "HIGH" ? "danger" : atk.integrity_impact === "MEDIUM" ? "warning" : atk.integrity_impact === "LOW" ? "neutral" : "success"}>
                    Integrity impact: {atk.integrity_impact}
                  </Pill>
                </div>
                <p className="text-xs text-ink-400">
                  Injected: {atk.injected_keywords.join(", ")}
                  {atk.flags_triggered.length > 0 && (
                    <> — flags: {atk.flags_triggered.map((f) => f.replace(/_/g, " ")).join(", ")}</>
                  )}
                </p>
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
