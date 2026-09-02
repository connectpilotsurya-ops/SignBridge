# SYNTHETIX HR — Proof Before Score

> Don't score the claim. Score the evidence.
> Rank candidates by the strength of their evidence, not simply by the presence of keywords.

An explainable candidate-**ranking** tool for recruiters — deliberately not an auto-shortlisting
one. Synthetix HR analyzes every candidate against the job requirements and produces an
evidence-backed ranking so recruiters can focus their attention where it matters: every match
traces back to a specific sentence in the resume, every anti-gaming flag traces back to specific
forensic evidence in the PDF, and the final `match_score` is computed by a deterministic,
auditable Python engine that the LLM never touches. The AI ranks. It never shortlists, rejects,
or hires — the recruiter always makes the final call, and can select any candidate for the next
stage regardless of their AI rank.

Built for the "AI Resume Screening Assistant" brief: *"Build an explainable candidate-analysis
tool that compares resumes with job requirements without reducing screening to an opaque LLM
score,"* extended with a later product-logic update: **ranking, not shortlisting** — the system
must never auto-filter candidates; it must rank every one of them and let a human decide who
advances.

## What makes this different from a wrapper around an LLM

- **The LLM never scores.** It interprets evidence — is this claim supported, is it direct or
  transferable — and hands structured, Pydantic-validated output to a plain Python scoring
  engine (`backend/app/scoring/engine.py`). Same inputs always produce the same score. You can
  read the whole scoring formula top to bottom; there's no model weight anywhere in it.
- **Anti-gaming is forensic, not vibes.** `backend/app/parsing/pdf_parser.py` reads font size,
  color, and position for every run of text in the PDF (via PyMuPDF), and
  `backend/app/integrity/detector.py` flags white-on-white text, tiny fonts, footer keyword
  stuffing, repeated-keyword cramming, and padded skills sections — all before a single term is
  matched against the job. Terms found only in a suspicious region are excluded from matching,
  not just down-weighted.
- **The system never accuses.** A Pydantic validator (`backend/app/schemas/assessment.py`)
  physically rejects any LLM output containing dishonesty language ("is lying"), personality
  judgments ("fast learner"), or similar — a claim that isn't backed by evidence is reported as
  a "claim-evidence mismatch," never as a character judgment.
- **The recruiter always has the final word.** Every analysis that trips a review condition
  (missing must-have, integrity risk, potential gaming) is marked `REVIEW_REQUIRED`. A
  recruiter's override is recorded *alongside* the system's original assessment, never over it —
  full audit trail, always.
- **Ranking, never shortlisting.** `backend/app/scoring/ranking.py` is a pure, deterministic
  function — no LLM, no randomness — that sorts every analyzed candidate by `match_score` (ties
  broken by `evidence_confidence`, then `document_integrity`) and labels each one with a
  descriptive `ranking_status` (`TOP_MATCH` / `STRONG_MATCH` / `POTENTIAL_MATCH` / `LOWER_MATCH` /
  `HUMAN_REVIEW_REQUIRED`). It never removes anyone from the list. A recruiter's own "select for
  next stage" decision (`candidate_selections`, spec-required field name `selection_status`, never
  the forbidden `ai_shortlisted`) is stored entirely separately and can be set on *any* rank —
  the flagship example: a #41-ranked candidate can be marked `SELECTED` while the AI's rank and
  score for them stay exactly as computed. See `/dashboard/jobs/[jobId]/ranking` and
  `GET /api/jobs/{job_id}/ranking`.

## Try it in under two minutes

```bash
# Terminal 1 — backend (auto-seeds demo data on first boot)
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev
```

Open `http://localhost:3000`, click **"Use the demo account"** on the login screen (or log in
manually with `demo@synthetixhr.example` / `SynthetixDemo!1`), and you'll land on a dashboard
with one job and four already-analyzed candidates spanning the full range the system is built to
show:

| Candidate | What it demonstrates |
|---|---|
| Priya Natarajan | Genuine, narrative-backed evidence for most requirements — a real strong candidate |
| Marcus Webb | An honest partial fit with a real gap (no AWS evidence) — correctly routed to human review |
| Dana Whitfield | Lists the right skills but never demonstrates them narratively — "claims aren't proof," not flagged as dishonest, just weakly evidenced |
| Alex Chen | A real resume with AWS/SQL/Kubernetes/Terraform/React stuffed in as invisible white-on-white text — the flagship anti-gaming story, already shows a recorded recruiter override in its audit trail |

Click **"View full AI ranking →"** from that job to see the primary ranking dashboard: summary
cards (top match, average match, highest evidence confidence, candidates requiring review), the
full ranked table with a "Select for next stage" action per candidate, and a 2-4 candidate
"Compare" view with a "why ranks above" explanation.

From there: **Adversarial simulator** in the sidebar runs all six gaming techniques against a
bundled clean resume (or one you upload) live, in real time — nothing pre-canned.

No API keys, no external accounts, no database server. Everything above runs against a local
SQLite file and an in-process mock reasoner that obeys the exact same evidence-only rules the
real Gemini prompt does.

## Architecture

```
resume PDF ──► PyMuPDF forensic parse ──► anti-gaming detector ──► claim extraction
                                                                          │
job description ──► requirement extraction ──────────────────────► per-requirement
                                                                     LLM assessment
                                                                          │
                              ┌───────────────────────────────────────────┘
                              ▼
              deterministic Python scoring engine (zero LLM involvement)
                              │
                    human-review gate (pure rule evaluation)
                              │
        capability graph · interview questions · executive summary
                              │
                              ▼
          deterministic ranking engine (app/scoring/ranking.py — zero LLM,
             zero randomness: sorts by match_score, tie-breaks on
             evidence_confidence then document_integrity)
                              │
                              ▼
     ranked candidate pool (every analyzed candidate, never a shortlist)
                              │
                              ▼
   recruiter selection for next stage (candidate_selections — stored
      separately; never overwrites the AI's rank/score/ranking_status)
```

Full pipeline framing from the spec update: **AI understands → evidence validates → rules score
→ system ranks → evidence explains → recruiter selects → interview/hiring process.**

Every external dependency has two adapters, selected by `DEMO_MODE` in `backend/.env`:

| Dependency | Demo adapter (default) | Real adapter |
|---|---|---|
| LLM | `app/llm/mock.py` — deterministic, rule-based, obeys the same evidence-only constitution as the real prompt | `app/llm/gemini_client.py` — Gemini 2.5 Flash, structured output validated against the same Pydantic schemas, retries once then fails safe to the mock logic for that one item |
| Embeddings / vector search | `app/embeddings/memory.py` — in-memory hashing embedder + cosine similarity | `app/embeddings/real.py` — BAAI/bge-m3 + Qdrant |
| Persistence + file storage | `app/persistence/sqlite_store.py` + local disk | `app/persistence/supabase_store.py` — Postgres with Row Level Security (`backend/db/schema.sql`) |

Every analysis result carries `"analysis_mode": "mock" | "real"` — which mode produced it is
never silently blurred. Flipping `DEMO_MODE=false` and supplying real credentials in
`backend/.env` (see `backend/.env.example`) switches every adapter with no code changes.

## Project structure

```
backend/
  app/
    parsing/        PyMuPDF forensic PDF parser
    integrity/       anti-gaming detector (deterministic)
    scoring/         scoring engine + human-review gate + ranking engine (all deterministic)
    llm/             mock + Gemini adapters, shared prompts, skill-relationship graph
    embeddings/      in-memory + Qdrant/BGE adapters
    persistence/     SQLite + Supabase stores (incl. ranking_snapshots, candidate_selections)
    services/        pipeline orchestration, career/adaptability analysis, ranking-view
                      assembly, adversarial simulator, demo-data seed
    api/             FastAPI routers (auth, jobs, resumes, analysis, adversarial) — ranking
                      lives under jobs (`/ranking`, `/ranking/history`) and selection under
                      analysis (`/api/applications/{id}/selection`)
    schemas/         Pydantic models — the single source of truth for every data contract
                      (ranking.py: RankedCandidate, RankingSummary, SelectionIn/Out)
  scripts/seed_demo.py   manual re-seed entry point
  tests/                 35 pytest cases across parsing, scoring, gating, the mock LLM, the
                          ranking engine, the ranking/selection API, the full API flow, and
                          the adversarial simulator
  db/schema.sql          full normalized Postgres schema + Row Level Security, for real mode

frontend/
  app/               Next.js 14 App Router pages, incl. dashboard/jobs/[jobId]/ranking
  components/         design-system primitives (ui.tsx), capability graph (SVG), app shell
  lib/                API client, auth context
  types/api.ts        TypeScript mirror of the backend's Pydantic schemas
```

## Visual design

The UI follows a dark, minimalist studio aesthetic (near-black ground, restrained monochrome
surfaces, a single cool violet accent reserved for emphasis and interactive highlights, and
functional color — green/amber/red — reserved strictly for score and status signal). It's
implemented as design tokens in `frontend/tailwind.config.ts` (`bg`, `surface`, `border`, `ink.*`,
`primary`, `accent`, `success`/`warning`/`danger`), so the whole app reskins from one place rather
than per-page overrides.

## Running the tests

```bash
cd backend
source .venv/bin/activate
python -m pytest tests/ -v
```

35 cases covering: forensic PDF parsing and every anti-gaming technique (including a false-positive
guard so a normal skills list is never flagged), deterministic score reproducibility and the
human-review gate, the mock LLM's JD-extraction correctness (including a regression test for an
inline "Must-have: X, Y, Z." header format that initially broke extraction), the Pydantic
validator that blocks dishonesty/personality language from ever reaching a response, the full HTTP
API flow (signup → job → analyze → upload → candidates → decision → audit trail → blind mode), all
six adversarial attack types against the bundled clean sample resume, the ranking engine's
sort/tie-break/threshold logic (pure unit tests, no I/O), and the ranking/selection API (every
uploaded candidate appears — never a shortlist — sorted correctly, the forbidden `ai_shortlisted`
field never appears, a recruiter selection never mutates the AI's rank or score, and ranking
history survives a requirements re-analysis).

`frontend/e2e_smoke.py` is a Playwright script that drives the actual rendered UI against a live
backend through the full user journey (login → dashboard → job detail → AI ranking dashboard →
select a candidate for the next stage → compare candidates → candidate detail → override decision
→ adversarial simulator → create+analyze a new job) — useful for a full-stack sanity check after
changes; run it with both servers up: `python frontend/e2e_smoke.py`.

## Known limitations (hackathon-scope honesty)

- The SQLite demo store simplifies `db/schema.sql`'s fully normalized entity list — nested
  analysis output (requirement assessments, career trajectory, capability graph, integrity
  flags, interview questions) is stored as JSON columns on one `analysis_runs` row rather than
  fully normalized tables. Nothing in the structured output is lost; it round-trips exactly.
  Real mode (Supabase) uses the fully normalized schema with Row Level Security.
- Career-trajectory parsing looks for year anchors (`"2021 - Present"`, `"2021-2024"`) in the
  experience section via regex, not an LLM — deliberately, so it can never predict future
  performance or attach a personality label to a resume, per spec's explicit constraint. It's
  accordingly a best-effort heuristic, not a full date parser.
- Blind review mode is a per-view toggle (on the candidate list) rather than an org-wide
  setting — see the Settings page for the reasoning.
- `npm audit` flags a handful of `next@14.2.x` advisories, mostly around self-hosted
  Server-Components edge cases (cache poisoning, middleware rewrites) that don't apply to this
  app's usage. A full fix requires the Next 15/16 major upgrade, out of scope here — worth doing
  before any real production deployment.
- `CandidateStatus` (the recruiter's own decision/override classification, e.g. `strong_match`,
  `review_required`) and `RankingStatus` (the AI's descriptive ranking tier, e.g. `TOP_MATCH`,
  `LOWER_MATCH`) are intentionally two separate enums rather than one merged vocabulary — they
  answer two different questions ("what did the recruiter decide" vs. "how did the ranking engine
  describe this candidate's evidence") and conflating them would blur exactly the AI/human
  boundary this spec update exists to enforce.
- Real mode's `SupabaseStore` ranking/selection methods (`db/schema.sql`'s `ranking_snapshots` and
  `candidate_selections` tables) are written correctly against the documented `supabase-py` API
  but, like the rest of `SupabaseStore`, have not been exercised against a live Supabase project
  in this sandbox — same honesty note as the rest of real mode.

## Environment variables

See `backend/.env.example` for the full list. The only one that matters for the demo is
`DEMO_MODE=true` (the default). Everything else (`GEMINI_API_KEY`, `SUPABASE_URL`, `QDRANT_URL`,
...) is only read when `DEMO_MODE=false`.

For the frontend, `frontend/.env.local` sets `NEXT_PUBLIC_API_BASE_URL` (defaults to
`http://localhost:8000`).
