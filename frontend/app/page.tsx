import Link from "next/link";

const PILLARS = [
  {
    n: "01",
    title: "Evidence, not adjectives",
    body: "Every match traces back to the exact line in the resume that supports it. No hidden LLM black-box score without sentence proof.",
    icon: "🔍",
  },
  {
    n: "02",
    title: "Anti-gaming forensic engine",
    body: "White-on-white text, tiny fonts, footer keyword stuffing, and fake skill cramming are forensically stripped out before scoring.",
    icon: "🛡️",
  },
  {
    n: "03",
    title: "Ranking, not auto-shortlisting",
    body: "The AI never automatically shortlists, rejects, or hires candidates. It ranks every candidate so recruiters make informed decisions.",
    icon: "📊",
  },
];

const PIPELINE = [
  "PyMuPDF Forensic Parse",
  "Anti-Gaming Detection",
  "Requirement Matching",
  "Pydantic Validation",
  "Deterministic Rule Engine",
  "Recruiter Audit Decision",
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-gradient-to-b from-indigo-50/50 via-bg to-bg text-ink-900 selection:bg-primary-soft selection:text-primary">
      {/* Header Navigation */}
      <header className="max-w-7xl mx-auto px-6 py-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-9 w-9 rounded-xl bg-gradient-to-tr from-primary via-indigo-500 to-accent flex items-center justify-center shadow-md shadow-primary/25">
            <span className="text-white font-display font-black text-sm tracking-widest">S</span>
          </div>
          <div className="leading-tight">
            <span className="font-display font-extrabold text-base text-ink-900 tracking-tight">
              SYNTHETIX <span className="text-primary font-semibold text-xs px-1.5 py-0.5 rounded-md bg-primary-soft">HR</span>
            </span>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Link
            href="/login"
            className="text-sm font-semibold text-ink-700 hover:text-primary transition-colors"
          >
            Log in
          </Link>
          <Link
            href="/signup"
            className="text-sm font-semibold text-white bg-primary hover:bg-primary-hover rounded-xl px-5 py-2.5 shadow-md shadow-primary/25 transition-all"
          >
            Get started
          </Link>
        </div>
      </header>

      {/* Hero Section */}
      <section className="max-w-5xl mx-auto px-6 pt-16 pb-24 text-center">
        <div className="inline-flex items-center gap-2 rounded-full border border-border-strong bg-white px-4 py-1.5 text-xs font-bold text-primary mb-8 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
          PROOF BEFORE SCORE — EXPLAINABLE CANDIDATE RECRUITMENT
        </div>

        <h1 className="font-display text-5xl sm:text-6xl md:text-7xl font-extrabold text-ink-900 leading-[1.05] tracking-tight max-w-4xl mx-auto">
          Don&rsquo;t score the claim.
          <br />
          Score <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary to-accent">the evidence.</span>
        </h1>

        <p className="mt-8 text-lg md:text-xl text-ink-500 max-w-2xl mx-auto leading-relaxed font-normal">
          Synthetix HR analyzes every candidate against job requirements with sentence-level proof,
          forensic anti-gaming checks, and an audit-proof deterministic scoring engine.
        </p>

        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          <Link
            href="/login"
            className="group inline-flex items-center gap-2.5 text-sm font-bold text-white bg-primary hover:bg-primary-hover rounded-xl px-6 py-3.5 shadow-lg shadow-primary/30 transition-all hover:scale-[1.02]"
          >
            Use Demo Account
            <span className="transition-transform group-hover:translate-x-1">→</span>
          </Link>
          <Link
            href="/signup"
            className="inline-flex items-center gap-2 text-sm font-semibold text-ink-700 bg-white hover:bg-slate-50 border border-border rounded-xl px-6 py-3.5 shadow-sm transition-all"
          >
            Create Free Account
          </Link>
        </div>
      </section>

      {/* Interactive Candidate Pipeline Ribbon */}
      <section className="border-y border-border bg-white/70 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="text-center text-xs font-bold text-ink-400 uppercase tracking-widest mb-6">
            AUDIT-PROOF EVALUATION WORKFLOW
          </div>
          <div className="flex flex-wrap items-center justify-center gap-3 text-xs font-semibold">
            {PIPELINE.map((step, i) => (
              <div key={step} className="flex items-center gap-3">
                <span className="bg-primary-soft text-primary px-3 py-1.5 rounded-lg border border-primary/10">
                  {i + 1}. {step}
                </span>
                {i < PIPELINE.length - 1 && <span className="text-ink-300">→</span>}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pillars Section */}
      <section className="max-w-6xl mx-auto px-6 py-20">
        <div className="grid md:grid-cols-3 gap-6">
          {PILLARS.map((p) => (
            <div
              key={p.title}
              className="bg-white p-8 rounded-2xl border border-border shadow-card hover:shadow-pop hover:border-border-strong transition-all"
            >
              <div className="text-3xl mb-4">{p.icon}</div>
              <span className="font-mono text-xs font-bold text-primary">{p.n}</span>
              <h3 className="font-display font-bold text-ink-900 mt-2 mb-3 text-xl">{p.title}</h3>
              <p className="text-sm text-ink-500 leading-relaxed font-normal">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Callout Quote */}
      <section className="max-w-4xl mx-auto px-6 pb-24 text-center">
        <div className="bg-gradient-to-r from-primary-soft via-accent-soft to-primary-soft p-10 rounded-3xl border border-primary/20">
          <p className="font-display text-2xl md:text-3xl font-extrabold text-ink-900 leading-snug">
            &ldquo;The AI ranks by sentence evidence. It never shortlists or rejects.{" "}
            <span className="text-primary">The recruiter always makes the final call.&rdquo;</span>
          </p>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-border bg-white py-8">
        <div className="max-w-7xl mx-auto px-6 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-ink-500">
          <span className="font-bold text-ink-900">SYNTHETIX HR — Proof Before Score</span>
          <span>Explainable Resume Intelligence • Deterministic Scoring Engine</span>
        </div>
      </footer>
    </div>
  );
}
