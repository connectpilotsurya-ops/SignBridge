"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { Button, Card, TextInput } from "@/components/ui";

export default function SignupPage() {
  const { signup } = useAuth();
  const router = useRouter();
  const [organizationName, setOrganizationName] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await signup(email, password, organizationName, displayName);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50/60 via-bg to-indigo-50/30 flex flex-col items-center justify-center px-6 py-12">
      <div className="mb-8 flex flex-col items-center text-center">
        <Link href="/" className="flex items-center gap-3 group mb-2">
          <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-primary via-indigo-500 to-accent flex items-center justify-center shadow-lg shadow-primary/30">
            <span className="text-white font-display font-black text-base tracking-widest">S</span>
          </div>
          <span className="font-display font-extrabold text-xl text-ink-900 tracking-tight">
            SYNTHETIX <span className="text-primary font-semibold text-sm px-1.5 py-0.5 rounded-md bg-primary-soft">HR</span>
          </span>
        </Link>
        <span className="text-xs font-semibold text-ink-500 uppercase tracking-widest">
          Proof Before Score — Recruiter Workspace
        </span>
      </div>

      <Card className="w-full max-w-md p-8 bg-white/90 backdrop-blur-md shadow-xl border-border">
        <h1 className="font-display text-2xl font-bold text-ink-900">Create your account</h1>
        <p className="text-sm text-ink-500 mt-1 mb-6">
          Set up your organization & recruiter workspace in one step.
        </p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <TextInput
            label="Organization name"
            required
            value={organizationName}
            onChange={(e) => setOrganizationName(e.target.value)}
            placeholder="Acme Corp"
          />
          <TextInput
            label="Your name"
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Ada Recruiter"
          />
          <TextInput
            label="Work Email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@company.com"
          />
          <TextInput
            label="Password"
            type="password"
            required
            minLength={6}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="At least 6 characters"
          />
          {error && <p className="text-sm text-danger font-medium">{error}</p>}
          <Button type="submit" variant="primary" className="w-full shadow-md shadow-primary/25" disabled={loading}>
            {loading ? "Creating workspace…" : "Create Workspace"}
          </Button>
        </form>

        <p className="text-sm text-ink-500 mt-6 text-center">
          Already have an account?{" "}
          <Link href="/login" className="text-primary font-bold hover:underline">
            Log in
          </Link>
        </p>
      </Card>
    </div>
  );
}
