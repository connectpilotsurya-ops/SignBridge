"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { ReactNode } from "react";
import { useAuth } from "@/lib/auth-context";
import { Spinner } from "./ui";
import { QuickSearch } from "./QuickSearch";

function Logo() {
  return (
    <Link href="/dashboard" className="flex items-center gap-3 group">
      <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-primary via-indigo-500 to-accent flex items-center justify-center shadow-md shadow-primary/25 transition-transform group-hover:scale-105">
        <span className="text-white font-display font-black text-sm tracking-widest">S</span>
      </div>
      <div className="leading-tight">
        <div className="font-display font-extrabold text-base text-ink-900 tracking-tight flex items-center gap-1.5">
          SYNTHETIX <span className="text-primary font-semibold text-xs px-1.5 py-0.5 rounded-md bg-primary-soft">HR</span>
        </div>
        <div className="text-[10px] font-medium text-ink-400 tracking-wider uppercase">Proof before score</div>
      </div>
    </Link>
  );
}

const NAV_ITEMS = [
  { href: "/dashboard", label: "Jobs Pipeline", icon: "💼" },
  { href: "/dashboard/adversarial", label: "Adversarial Lab", icon: "🛡️" },
  { href: "/dashboard/settings", label: "Settings", icon: "⚙️" },
];

export function AppShell({ children }: { children: ReactNode }) {
  const { session, loading, logout } = useAuth();
  const pathname = usePathname();
  const router = useRouter();

  if (loading) {
    return (
      <div className="min-h-screen bg-bg flex items-center justify-center text-ink-400">
        <Spinner className="w-8 h-8 text-primary" />
      </div>
    );
  }

  const displaySession = session ?? {
    email: "Demo Recruiter",
    organizationName: "SYNTHETIX HR Demo",
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50/30 via-bg to-bg text-ink-900 flex flex-col antialiased">
      <QuickSearch />
      {/* Executive Glass Header */}
      <header className="sticky top-0 z-40 bg-surface/85 backdrop-blur-md border-b border-border/80 shadow-sm">
        <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
          <div className="flex items-center gap-8">
            <Logo />
            <div className="hidden lg:flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-50 text-emerald-700 text-xs font-semibold border border-emerald-200/60">
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              Engine Online (SQLite + Gemini Mock)
            </div>
          </div>

          <nav className="flex items-center gap-1.5 bg-bg/80 p-1.5 rounded-2xl border border-border/60">
            {NAV_ITEMS.map((item) => {
              const active = pathname === item.href || (item.href !== "/dashboard" && pathname.startsWith(item.href));
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all ${
                    active
                      ? "bg-surface text-primary shadow-sm font-semibold border border-border"
                      : "text-ink-500 hover:text-ink-900 hover:bg-surface/50"
                  }`}
                >
                  <span className="text-xs">{item.icon}</span>
                  {item.label}
                </Link>
              );
            })}
          </nav>

          <div className="flex items-center gap-4">
            <button
              onClick={() => {
                const event = new KeyboardEvent("keydown", { key: "k", ctrlKey: true });
                window.dispatchEvent(event);
              }}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 border border-slate-200 text-xs text-ink-500 hover:text-ink-900 transition-colors"
            >
              <span>🔍 Quick Search</span>
              <kbd className="px-1.5 py-0.5 rounded bg-white font-mono text-[10px] text-ink-400 border border-slate-200">
                Ctrl+K
              </kbd>
            </button>

            <div className="hidden sm:flex flex-col text-right">
              <span className="text-xs font-bold text-ink-900">{displaySession.email}</span>
              <span className="text-[10px] text-ink-400 font-medium">{displaySession.organizationName}</span>
            </div>
            <div className="h-8 w-8 rounded-full bg-primary/10 text-primary font-bold text-xs flex items-center justify-center border border-primary/20 shadow-xs">
              {displaySession.email[0].toUpperCase()}
            </div>
            <button
              onClick={() => {
                logout();
                router.replace("/login");
              }}
              className="text-xs font-medium px-3 py-1.5 rounded-lg text-ink-500 hover:text-danger hover:bg-danger/10 transition-colors"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
        {children}
      </main>

      {/* Modern Footer */}
      <footer className="border-t border-border bg-surface/60 py-6 mt-12">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between text-xs text-ink-400 gap-4">
          <div className="flex items-center gap-2 font-medium">
            <span className="text-ink-900 font-bold">SYNTHETIX HR</span>
            <span>— Explainable Candidate Resume Intelligence</span>
          </div>
          <div className="flex items-center gap-4 text-ink-500 font-medium">
            <span>Deterministic Scoring</span>
            <span>•</span>
            <span>Forensic Anti-Gaming</span>
            <span>•</span>
            <span>Ranking Not Shortlisting</span>
          </div>
        </div>
      </footer>
    </div>
  );
}

