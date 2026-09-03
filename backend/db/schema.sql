-- Synthetix HR — Supabase Postgres schema (REAL MODE).
--
-- This is the production-style schema described in spec §6/§41: full
-- entity list, UUID keys, org-scoped RLS. It has been authored against
-- Supabase's documented RLS pattern (auth.uid() + a membership table) but
-- has NOT been executed against a live Supabase project from this sandbox
-- — there is no Supabase instance available here to test against. Review
-- it before running in production, same as you would any migration
-- written by a new team member.
--
-- DEMO_MODE (the default) does not use this file at all — it runs against
-- a local SQLite database with a deliberately simplified shape (nested
-- analysis output stored as JSON columns instead of fully normalized
-- tables). See app/persistence/sqlite_store.py and README "Known
-- limitations" for why, and adapt this file if you extend the demo.
--
-- Run this in the Supabase SQL editor, or via `supabase db push`.

create extension if not exists "pgcrypto";

drop table if exists auth_tokens cascade;
drop table if exists users cascade;
drop table if exists interview_verifications cascade;
drop table if exists interview_questions cascade;
drop table if exists candidate_selections cascade;
drop table if exists ranking_snapshots cascade;
drop table if exists audit_log cascade;
drop table if exists recruiter_decisions cascade;
drop table if exists candidate_scores cascade;
drop table if exists analysis_runs cascade;
drop table if exists skill_relationships cascade;
drop table if exists candidate_claims cascade;
drop table if exists resume_evidence cascade;
drop table if exists applications cascade;
drop table if exists resumes cascade;
drop table if exists candidates cascade;
drop table if exists job_requirements cascade;
drop table if exists jobs cascade;
drop table if exists organization_members cascade;
drop table if exists profiles cascade;
drop table if exists organizations cascade;

-- ── Authentication & Users ──────────────────────────────────────────────────

create table users (
    id uuid primary key default gen_random_uuid(),
    email text not null unique,
    password_hash text not null,
    display_name text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_users_email on users(email);

create table auth_tokens (
    id uuid primary key default gen_random_uuid(),
    user_id uuid not null references users(id) on delete cascade,
    token text not null unique,
    expires_at timestamptz not null,
    created_at timestamptz not null default now()
);

create index idx_auth_tokens_token on auth_tokens(token);

-- ── Organizations & membership ──────────────────────────────────────────

create table organizations (
    id uuid primary key default gen_random_uuid(),
    name text not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table profiles (
    id uuid primary key references users(id) on delete cascade,
    email text not null,
    display_name text,
    created_at timestamptz not null default now()
);

create table organization_members (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    user_id uuid not null references profiles(id) on delete cascade,
    role text not null check (role in ('owner', 'admin', 'recruiter', 'viewer')),
    created_at timestamptz not null default now(),
    unique (org_id, user_id)
);

create index idx_org_members_org on organization_members(org_id);
create index idx_org_members_user on organization_members(user_id);

-- ── Jobs & requirements ──────────────────────────────────────────────────

create table jobs (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    title text not null,
    department text default '',
    location text default '',
    employment_type text default 'full_time',
    description text not null,
    experience_requirement text default '',
    requirements_analyzed boolean not null default false,
    experience_years_min numeric,
    -- Spec update §12: bumped every time requirements are (re)analyzed, so
    -- ranking_snapshots rows can be tagged with the model version that
    -- produced them and old rankings are never silently overwritten.
    ranking_version integer not null default 1,
    created_by uuid references profiles(id),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_jobs_org on jobs(org_id);

create table job_requirements (
    id uuid primary key default gen_random_uuid(),
    job_id uuid not null references jobs(id) on delete cascade,
    org_id uuid not null references organizations(id) on delete cascade,
    name text not null,
    category text not null check (category in ('technical_skill','domain_skill','experience','education','certification')),
    importance text not null check (importance in ('must_have','preferred')),
    description text default '',
    normalized_terms jsonb not null default '[]',
    evidence_required boolean not null default true,
    weight numeric not null default 1.0,
    created_at timestamptz not null default now()
);

create index idx_job_requirements_job on job_requirements(job_id);

-- ── Candidates, resumes, applications ─────────────────────────────────────

create table candidates (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    display_name text,
    email text,
    phone text,
    created_at timestamptz not null default now()
);

create index idx_candidates_org on candidates(org_id);

create table resumes (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    candidate_id uuid not null references candidates(id) on delete cascade,
    file_name text not null,
    storage_path text not null,       -- Supabase Storage object path (private bucket)
    mime_type text default 'application/pdf',
    size_bytes bigint,
    status text not null default 'uploaded'
        check (status in ('uploaded','parsing','analyzing','completed','failed','review_required')),
    page_count int,
    created_at timestamptz not null default now()
);

create index idx_resumes_org on resumes(org_id);
create index idx_resumes_candidate on resumes(candidate_id);

create table applications (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    job_id uuid not null references jobs(id) on delete cascade,
    candidate_id uuid not null references candidates(id) on delete cascade,
    resume_id uuid references resumes(id) on delete set null,
    display_label text,                -- "Candidate #014" — assigned at creation, stable for blind mode
    status text not null default 'review_required'
        check (status in ('strong_match','potential_match','review_required','low_match')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_applications_org on applications(org_id);
create index idx_applications_job on applications(job_id);
create index idx_applications_status on applications(status);

-- ── Evidence & claims ──────────────────────────────────────────────────────

create table resume_evidence (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    resume_id uuid not null references resumes(id) on delete cascade,
    text text not null,
    page int not null,
    font_size numeric,
    color_hex text,
    bg_color_hex text,
    x numeric, y numeric, width numeric, height numeric,
    section text,
    visibility text check (visibility in ('visible','low_contrast','hidden','off_page')),
    created_at timestamptz not null default now()
);

create index idx_resume_evidence_resume on resume_evidence(resume_id);

create table candidate_claims (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    resume_id uuid not null references resumes(id) on delete cascade,
    skill_or_topic text not null,
    claim_text text not null,
    strength text not null check (strength in (
        'suspicious','skill_list_only','contextual_mention','certification',
        'project_evidence','work_experience','detailed_achievement','production_ownership'
    )),
    section text,
    evidence_ids uuid[] default '{}',
    created_at timestamptz not null default now()
);

create index idx_candidate_claims_resume on candidate_claims(resume_id);

create table skill_relationships (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    from_skill text not null,
    to_skill text not null,
    relationship_type text not null check (relationship_type in (
        'equivalent_to','related_to','adjacent_to','supports','prerequisite_for','transferable_to'
    )),
    base_strength numeric not null default 0.5,
    created_at timestamptz not null default now()
);

-- ── Analysis runs (one per resume x job pairing / application) ────────────

create table analysis_runs (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    mode text not null check (mode in ('mock','real')),
    status text not null default 'completed' check (status in ('completed','incomplete','failed')),
    incomplete_reason text,
    executive_summary text,
    match_score numeric,
    evidence_confidence numeric,
    document_integrity numeric,
    low_confidence boolean default false,
    human_review_required boolean default false,
    human_review_reasons jsonb default '[]',
    score_breakdown jsonb,              -- ScoreBreakdown
    requirement_analysis jsonb,          -- list[RequirementAssessment]
    claim_consistency jsonb,             -- list[ClaimEvidenceConsistency]
    career_trajectory jsonb,             -- CareerTrajectory
    adaptability jsonb,                  -- AdaptabilityIndicator
    capability_graph jsonb,              -- CapabilityGraph
    integrity_report jsonb,              -- IntegrityReport
    interview_questions jsonb,           -- list[InterviewQuestion]
    created_at timestamptz not null default now()
);

create index idx_analysis_runs_application on analysis_runs(application_id);
create index idx_analysis_runs_org on analysis_runs(org_id);

-- Convenience "current score" table so dashboard queries don't have to
-- pull the full analysis_runs JSON blobs — kept in sync by the service
-- layer whenever a new analysis_run completes.
create table candidate_scores (
    application_id uuid primary key references applications(id) on delete cascade,
    org_id uuid not null references organizations(id) on delete cascade,
    match_score numeric not null,
    evidence_confidence numeric not null,
    document_integrity numeric not null,
    status text not null,
    updated_at timestamptz not null default now()
);

-- ── Recruiter decisions & audit ────────────────────────────────────────────

create table recruiter_decisions (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    original_status text not null,
    decision text not null check (decision in ('agree','override','needs_further_review')),
    final_status text not null,
    reason text,
    recruiter_id uuid references profiles(id),
    created_at timestamptz not null default now()
);

create index idx_recruiter_decisions_application on recruiter_decisions(application_id);

create table audit_log (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    action text not null,
    object_type text not null,
    object_id text not null,
    user_id uuid references profiles(id),
    metadata jsonb default '{}',
    created_at timestamptz not null default now()
);

create index idx_audit_log_org on audit_log(org_id);
create index idx_audit_log_object on audit_log(object_type, object_id);

-- ── Ranking & recruiter selection — spec update "ranking, not shortlisting" ─
-- Two deliberately separate concepts, never merged into one table:
--   ranking_snapshots     — the AI's own evidence-backed rank/score, an
--                            immutable append-only history (spec update §12).
--   candidate_selections  — the recruiter's own pick for the next hiring
--                            stage. Any rank can be selected regardless of
--                            position; writing here never touches
--                            analysis_runs or ranking_snapshots (spec §11).

create table ranking_snapshots (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    job_id uuid not null references jobs(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    analysis_run_id uuid references analysis_runs(id) on delete set null,
    rank integer not null,
    match_score numeric not null,
    evidence_confidence numeric not null,
    document_integrity numeric not null,
    ranking_status text not null check (
        ranking_status in ('top_match','strong_match','potential_match','lower_match','human_review_required')
    ),
    ranking_version integer not null,
    created_at timestamptz not null default now()
);

create index idx_ranking_snapshots_job on ranking_snapshots(job_id, ranking_version, rank);

create table candidate_selections (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    recruiter_id uuid references profiles(id),
    selection_status text not null check (selection_status in ('selected','not_selected','under_review')),
    selection_reason text,
    selected_at timestamptz not null default now(),
    unique (application_id)
);

create index idx_candidate_selections_application on candidate_selections(application_id);

-- ── AI Interview Verification Engine ──────────────────────────────────────

create table interview_questions (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    claim_id text,
    requirement_id text,
    question text not null,
    purpose text,
    evidence_gap text,
    verification_category text not null,
    expected_evidence text default '',
    priority integer default 1,
    status text not null default 'generated' check (status in ('generated','reviewed','asked','verified','not_verified','skipped')),
    recruiter_notes text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index idx_interview_questions_application on interview_questions(application_id);

create table interview_verifications (
    id uuid primary key default gen_random_uuid(),
    org_id uuid not null references organizations(id) on delete cascade,
    application_id uuid not null references applications(id) on delete cascade,
    claim_id text,
    question_id uuid not null references interview_questions(id) on delete cascade,
    recruiter_id uuid references profiles(id),
    verification_status text not null check (verification_status in ('verified','partially_verified','not_verified','inconclusive')),
    verification_notes text default '',
    verified_at timestamptz not null default now(),
    created_at timestamptz not null default now()
);

create index idx_interview_verifications_application on interview_verifications(application_id);

-- ══════════════════════════════════════════════════════════════════════════
-- Row Level Security — org isolation (spec §7/§41)
-- ══════════════════════════════════════════════════════════════════════════

alter table organizations enable row level security;
alter table organization_members enable row level security;
alter table jobs enable row level security;
alter table job_requirements enable row level security;
alter table candidates enable row level security;
alter table resumes enable row level security;
alter table applications enable row level security;
alter table resume_evidence enable row level security;
alter table candidate_claims enable row level security;
alter table skill_relationships enable row level security;
alter table analysis_runs enable row level security;
alter table candidate_scores enable row level security;
alter table recruiter_decisions enable row level security;
alter table audit_log enable row level security;
alter table ranking_snapshots enable row level security;
alter table candidate_selections enable row level security;

-- Helper: is the current auth.uid() a member of the given org?
create or replace function is_org_member(target_org uuid)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1 from organization_members
    where org_id = target_org and user_id = auth.uid()
  );
$$;

-- Helper: does the current user have at least `min_role` in the org?
-- Role rank: viewer < recruiter < admin < owner.
create or replace function has_org_role(target_org uuid, min_role text)
returns boolean
language sql
security definer
stable
as $$
  select exists (
    select 1 from organization_members
    where org_id = target_org
      and user_id = auth.uid()
      and case min_role
            when 'viewer' then role in ('viewer','recruiter','admin','owner')
            when 'recruiter' then role in ('recruiter','admin','owner')
            when 'admin' then role in ('admin','owner')
            when 'owner' then role = 'owner'
            else false
          end
  );
$$;

-- organizations: members can see their own org
create policy org_select on organizations for select
    using (is_org_member(id));
create policy org_update on organizations for update
    using (has_org_role(id, 'admin'));

-- organization_members: members can see fellow members of their own org
create policy org_members_select on organization_members for select
    using (is_org_member(org_id));
create policy org_members_write on organization_members for all
    using (has_org_role(org_id, 'admin'))
    with check (has_org_role(org_id, 'admin'));

-- Every remaining table follows the same shape: select/insert/update/delete
-- gated on org membership (read) or recruiter+ role (write). Repeated per
-- table because Postgres RLS policies aren't inherited.

create policy jobs_select on jobs for select using (is_org_member(org_id));
create policy jobs_write on jobs for insert with check (has_org_role(org_id, 'recruiter'));
create policy jobs_update on jobs for update using (has_org_role(org_id, 'recruiter'));
create policy jobs_delete on jobs for delete using (has_org_role(org_id, 'admin'));

create policy job_requirements_select on job_requirements for select using (is_org_member(org_id));
create policy job_requirements_write on job_requirements for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy candidates_select on candidates for select using (is_org_member(org_id));
create policy candidates_write on candidates for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy resumes_select on resumes for select using (is_org_member(org_id));
create policy resumes_write on resumes for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy applications_select on applications for select using (is_org_member(org_id));
create policy applications_write on applications for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy resume_evidence_select on resume_evidence for select using (is_org_member(org_id));
create policy resume_evidence_write on resume_evidence for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy candidate_claims_select on candidate_claims for select using (is_org_member(org_id));
create policy candidate_claims_write on candidate_claims for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy skill_relationships_select on skill_relationships for select using (is_org_member(org_id));

create policy analysis_runs_select on analysis_runs for select using (is_org_member(org_id));
create policy analysis_runs_write on analysis_runs for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

create policy candidate_scores_select on candidate_scores for select using (is_org_member(org_id));

create policy recruiter_decisions_select on recruiter_decisions for select using (is_org_member(org_id));
create policy recruiter_decisions_write on recruiter_decisions for insert
    with check (has_org_role(org_id, 'recruiter'));

create policy audit_log_select on audit_log for select using (is_org_member(org_id));
-- audit_log inserts happen via the backend's service-role key only (never
-- from the browser), so no insert policy is granted to authenticated users.

create policy ranking_snapshots_select on ranking_snapshots for select using (is_org_member(org_id));
-- ranking_snapshots is written only by the backend's ranking engine
-- (service-role key), never directly by a client — no insert/update policy
-- for authenticated users, matching audit_log's pattern above.

create policy candidate_selections_select on candidate_selections for select using (is_org_member(org_id));
create policy candidate_selections_write on candidate_selections for all
    using (has_org_role(org_id, 'recruiter')) with check (has_org_role(org_id, 'recruiter'));

-- profiles: a user can always read/update their own profile row
alter table profiles enable row level security;
create policy profiles_self_select on profiles for select using (id = auth.uid());
create policy profiles_self_update on profiles for update using (id = auth.uid());
