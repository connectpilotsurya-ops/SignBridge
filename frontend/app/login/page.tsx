"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { ApiError } from "@/lib/api";
import { Button, Card, TextInput } from "@/components/ui";

export default function LoginPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleDemoLogin() {
    setError(null);
    setLoading(true);
    try {
      await login("demo@synthetixhr.example", "SynthetixDemo!1");
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not sign in to the demo account.");
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
        <h1 className="font-display text-2xl font-bold text-ink-900">Welcome back</h1>
        <p className="text-sm text-ink-500 mt-1 mb-6">Log in to access explainable candidate rankings.</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <TextInput
            label="Email Address"
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
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            placeholder="••••••••"
          />
          {error && <p className="text-sm text-danger font-medium">{error}</p>}
          <Button type="submit" variant="primary" className="w-full shadow-md shadow-primary/25" disabled={loading}>
            {loading ? "Signing in…" : "Log in to Dashboard"}
          </Button>
        </form>

        <div className="flex items-center gap-3 my-6">
          <div className="h-px flex-1 bg-border" />
          <span className="text-xs font-semibold text-ink-400 uppercase">Instant Exploration</span>
          <div className="h-px flex-1 bg-border" />
        </div>

        <Button
          variant="secondary"
          className="w-full font-semibold border-primary/30 text-primary hover:bg-primary-soft"
          onClick={handleDemoLogin}
          disabled={loading}
        >
          🚀 Use Demo Account (Pre-loaded with 4 candidates)
        </Button>
        <p className="text-xs text-ink-400 mt-2 text-center">
          Includes genuine fit, gap analysis, claim mismatch & forensic white-text gaming.
        </p>

        <p className="text-sm text-ink-500 mt-6 text-center">
          Don&rsquo;t have an account?{" "}
          <Link href="/signup" className="text-primary font-bold hover:underline">
            Sign up now
          </Link>
        </p>
      </Card>
    </div>
  );
}
