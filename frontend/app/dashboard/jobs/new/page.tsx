"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, ApiError } from "@/lib/api";
import type { JobOut } from "@/types/api";
import { Button, Card, PageHeader, TextArea, TextInput } from "@/components/ui";

export default function NewJobPage() {
  const router = useRouter();
  const [title, setTitle] = useState("");
  const [department, setDepartment] = useState("");
  const [location, setLocation] = useState("");
  const [experienceRequirement, setExperienceRequirement] = useState("");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const job = await api.post<JobOut>("/api/jobs", {
        title,
        department,
        location,
        description,
        experience_requirement: experienceRequirement,
      });
      router.push(`/dashboard/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not create job.");
      setLoading(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <PageHeader
        title="New job"
        description="Paste the job description as-is. On the next screen you'll extract must-have vs. preferred requirements before uploading any resumes."
      />
      <Card className="p-6">
        <form onSubmit={handleSubmit} className="space-y-4">
          <TextInput
            label="Job title"
            required
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Backend Software Engineer"
          />
          <div className="grid grid-cols-2 gap-4">
            <TextInput
              label="Department"
              value={department}
              onChange={(e) => setDepartment(e.target.value)}
              placeholder="Engineering"
            />
            <TextInput
              label="Location"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              placeholder="Remote"
            />
          </div>
          <TextInput
            label="Experience requirement"
            value={experienceRequirement}
            onChange={(e) => setExperienceRequirement(e.target.value)}
            placeholder="3+ years of professional backend experience"
            hint="Used to extract a minimum-years threshold — e.g. '3+ years'."
          />
          <TextArea
            label="Job description"
            required
            rows={10}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={"We are hiring a Backend Software Engineer...\nMust-have: Python, SQL, Docker, AWS.\nPreferred: Kubernetes, Terraform, React."}
          />
          {error && <p className="text-sm text-danger">{error}</p>}
          <div className="flex gap-3">
            <Button type="submit" disabled={loading}>
              {loading ? "Creating…" : "Create job"}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
}
