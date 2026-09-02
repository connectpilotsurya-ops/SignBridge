"use client";

import { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";
import type { CandidateStatus, IntegrityCategory, MatchStatus, RankingStatus, SelectionStatus } from "@/types/api";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <div className={`bg-surface border border-border rounded-2xl shadow-card ${className}`}>
      {children}
    </div>
  );
}

export function Button({
  variant = "primary",
  size = "md",
  className = "",
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "accent";
  size?: "sm" | "md" | "lg";
}) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap";
  const sizes = {
    sm: "text-sm px-3 py-1.5",
    md: "text-sm px-4 py-2.5",
    lg: "text-base px-5 py-3",
  };
  const variants = {
    primary: "bg-primary text-white hover:bg-primary-hover shadow-sm shadow-primary/20",
    accent: "bg-accent text-white hover:bg-accent-hover shadow-sm shadow-accent/20",
    secondary: "bg-surface text-ink-700 border border-border hover:bg-surface-raised",
    ghost: "text-ink-500 hover:bg-surface-raised hover:text-ink-900",
    danger: "bg-danger text-white hover:opacity-90",
  };
  return (
    <button className={`${base} ${sizes[size]} ${variants[variant]} ${className}`} {...props}>
      {children}
    </button>
  );
}

export function TextInput({
  label,
  hint,
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label?: string; hint?: string }) {
  return (
    <label className="block">
      {label && <span className="block text-sm font-medium text-ink-700 mb-1.5">{label}</span>}
      <input
        className={`w-full rounded-xl border border-border bg-surface px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 ${className}`}
        {...props}
      />
      {hint && <span className="block text-xs text-ink-400 mt-1">{hint}</span>}
    </label>
  );
}

export function TextArea({
  label,
  hint,
  className = "",
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; hint?: string }) {
  return (
    <label className="block">
      {label && <span className="block text-sm font-medium text-ink-700 mb-1.5">{label}</span>}
      <textarea
        className={`w-full rounded-xl border border-border bg-surface px-3.5 py-2.5 text-sm text-ink-900 placeholder:text-ink-300 outline-none focus:border-primary focus:ring-2 focus:ring-primary/15 ${className}`}
        {...props}
      />
      {hint && <span className="block text-xs text-ink-400 mt-1">{hint}</span>}
    </label>
  );
}

export function Pill({
  children,
  tone = "neutral",
  className = "",
}: {
  children: ReactNode;
  tone?: "neutral" | "primary" | "accent" | "success" | "warning" | "danger";
  className?: string;
}) {
  const tones = {
    neutral: "bg-slate-100 text-ink-700 border-border",
    primary: "bg-primary-soft text-primary border-transparent font-semibold",
    accent: "bg-accent-soft text-accent border-transparent font-semibold",
    success: "bg-success-soft text-success border-transparent font-semibold",
    warning: "bg-warning-soft text-warning border-transparent font-semibold",
    danger: "bg-danger-soft text-danger border-transparent font-semibold",
  };
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2.5 py-1 text-xs font-medium ${tones[tone]} ${className}`}
    >
      {children}
    </span>
  );
}

const CANDIDATE_STATUS_MAP: Record<CandidateStatus, { label: string; tone: "success" | "primary" | "warning" | "danger" }> = {
  strong_match: { label: "Strong match", tone: "success" },
  potential_match: { label: "Potential match", tone: "primary" },
  review_required: { label: "Review required", tone: "warning" },
  low_match: { label: "Low match", tone: "danger" },
};

export function CandidateStatusBadge({ status }: { status: CandidateStatus }) {
  const meta = CANDIDATE_STATUS_MAP[status];
  return <Pill tone={meta.tone}>{meta.label}</Pill>;
}

const MATCH_STATUS_MAP: Record<MatchStatus, { label: string; tone: "success" | "primary" | "warning" | "danger" | "neutral" }> = {
  exact_match: { label: "Exact match", tone: "success" },
  equivalent_match: { label: "Equivalent match", tone: "success" },
  partial_match: { label: "Partial match", tone: "primary" },
  transferable: { label: "Transferable", tone: "warning" },
  not_evidenced: { label: "Not evidenced", tone: "neutral" },
  conflicting: { label: "Conflicting", tone: "danger" },
  potential_gaming: { label: "Potential gaming", tone: "danger" },
  human_review: { label: "Needs human review", tone: "warning" },
};

export function MatchStatusBadge({ status }: { status: MatchStatus }) {
  const meta = MATCH_STATUS_MAP[status] ?? { label: status, tone: "neutral" as const };
  return <Pill tone={meta.tone}>{meta.label}</Pill>;
}

const INTEGRITY_MAP: Record<IntegrityCategory, { label: string; tone: "success" | "warning" | "danger" }> = {
  normal: { label: "Normal", tone: "success" },
  suspicious: { label: "Suspicious", tone: "warning" },
  high_risk: { label: "High risk", tone: "danger" },
};

export function IntegrityBadge({ category }: { category: IntegrityCategory }) {
  const meta = INTEGRITY_MAP[category];
  return <Pill tone={meta.tone}>{meta.label}</Pill>;
}

// Spec update "ranking, not shortlisting": a descriptive ranking tier,
// never a hiring decision. Deliberately distinct wording from
// CandidateStatusBadge above — "lower match" not "rejected", etc.
const RANKING_STATUS_MAP: Record<RankingStatus, { label: string; tone: "success" | "primary" | "accent" | "warning" | "danger" }> = {
  top_match: { label: "Top match", tone: "success" },
  strong_match: { label: "Strong match", tone: "primary" },
  potential_match: { label: "Potential match", tone: "accent" },
  lower_match: { label: "Lower match", tone: "warning" },
  human_review_required: { label: "Human review required", tone: "danger" },
};

export function RankingStatusBadge({ status }: { status: RankingStatus }) {
  const meta = RANKING_STATUS_MAP[status];
  return <Pill tone={meta.tone}>{meta.label}</Pill>;
}

// A recruiter's own pick for the next hiring stage — stored entirely
// separately from ranking_status above. `null` means no decision has been
// recorded yet (not "not selected").
const SELECTION_STATUS_MAP: Record<SelectionStatus, { label: string; tone: "success" | "warning" | "neutral" }> = {
  selected: { label: "Selected for next stage", tone: "success" },
  not_selected: { label: "Not selected", tone: "neutral" },
  under_review: { label: "Under review", tone: "warning" },
};

export function SelectionStatusBadge({ status }: { status: SelectionStatus | null }) {
  if (!status) return <Pill tone="neutral">No selection yet</Pill>;
  const meta = SELECTION_STATUS_MAP[status];
  return <Pill tone={meta.tone}>{meta.label}</Pill>;
}

export function ScoreBar({
  label,
  value,
  max = 100,
  tone = "primary",
}: {
  label: string;
  value: number;
  max?: number;
  tone?: "primary" | "accent" | "success" | "warning" | "danger";
}) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100));
  const bar = {
    primary: "bg-primary",
    accent: "bg-accent",
    success: "bg-success",
    warning: "bg-warning",
    danger: "bg-danger",
  }[tone];
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1">
        <span className="text-ink-500">{label}</span>
        <span className="font-medium text-ink-700">
          {value.toFixed(1)}
          <span className="text-ink-400"> / {max}</span>
        </span>
      </div>
      <div className="h-2 w-full rounded-full bg-bg overflow-hidden">
        <div className={`h-full rounded-full ${bar}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function scoreTone(score: number): "success" | "primary" | "warning" | "danger" {
  if (score >= 75) return "success";
  if (score >= 55) return "primary";
  if (score >= 35) return "warning";
  return "danger";
}

export function ScoreGauge({ score, size = 96, label }: { score: number; size?: number; label?: string }) {
  const tone = scoreTone(score);
  const color = { success: "#10B981", primary: "#5D5FEF", warning: "#F59E0B", danger: "#EF4444" }[tone];
  const radius = size / 2 - 8;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - Math.max(0, Math.min(100, score)) / 100);
  return (
    <div className="flex flex-col items-center gap-1" style={{ width: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle cx={size / 2} cy={size / 2} r={radius} stroke="#E2E8F0" strokeWidth={8} fill="none" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={color}
          strokeWidth={8}
          fill="none"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
        <text x="50%" y="50%" textAnchor="middle" dy="0.35em" fontSize={size / 4} fontWeight={700} fill="#0F172A">
          {Math.round(score)}
        </text>
      </svg>
      {label && <span className="text-xs text-ink-500 text-center">{label}</span>}
    </div>
  );
}

export function Spinner({ className = "" }: { className?: string }) {
  return (
    <svg className={`animate-spin ${className}`} viewBox="0 0 24 24" fill="none">
      <circle className="opacity-20" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3" />
      <path d="M22 12a10 10 0 0 0-10-10" stroke="currentColor" strokeWidth="3" strokeLinecap="round" />
    </svg>
  );
}

export function EmptyState({ title, description, action }: { title: string; description?: string; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center justify-center text-center py-16 px-6">
      <h3 className="font-display font-semibold text-ink-900 text-lg">{title}</h3>
      {description && <p className="text-sm text-ink-500 mt-1.5 max-w-sm">{description}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function PageHeader({
  title,
  description,
  actions,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="flex items-start justify-between gap-4 mb-8">
      <div>
        <h1 className="font-display text-2xl font-bold text-ink-900">{title}</h1>
        {description && <p className="text-sm text-ink-500 mt-1.5 max-w-2xl">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2 shrink-0">{actions}</div>}
    </div>
  );
}
