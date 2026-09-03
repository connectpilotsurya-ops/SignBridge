"""
DEMO_MODE persistence — local SQLite, zero external accounts.

Deliberately simplified relative to db/schema.sql (spec §6's full entity
list): nested analysis output (requirement assessments, career
trajectory, capability graph, integrity flags, interview questions) is
stored as JSON columns on `analysis_runs` rather than fully normalized
into their own tables. Nothing in the structured Pydantic output is lost
— it round-trips exactly — this is a storage-shape simplification for
hackathon-speed development, not a feature cut. See README "Known
limitations". Swapping to real Supabase (app/persistence/supabase_store.py)
uses the fully normalized schema in db/schema.sql.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.config import Settings

SCHEMA = """
create table if not exists organizations (
    id text primary key,
    name text not null,
    created_at text not null
);

create table if not exists profiles (
    id text primary key,
    email text not null unique,
    display_name text,
    password_hash text,
    password_salt text,
    created_at text not null
);

create table if not exists organization_members (
    id text primary key,
    org_id text not null,
    user_id text not null,
    role text not null,
    created_at text not null
);

create table if not exists jobs (
    id text primary key,
    org_id text not null,
    title text not null,
    department text default '',
    location text default '',
    employment_type text default 'full_time',
    description text not null,
    experience_requirement text default '',
    requirements_json text not null default '[]',
    requirements_analyzed integer not null default 0,
    experience_years_min real,
    ranking_version integer not null default 1,
    created_at text not null
);

create table if not exists candidates (
    id text primary key,
    org_id text not null,
    display_name text,
    email text,
    created_at text not null
);

create table if not exists resumes (
    id text primary key,
    org_id text not null,
    candidate_id text not null,
    file_name text not null,
    storage_path text not null,
    status text not null default 'uploaded',
    page_count integer,
    failure_reason text,
    created_at text not null
);

create table if not exists applications (
    id text primary key,
    org_id text not null,
    job_id text not null,
    candidate_id text not null,
    resume_id text,
    display_label text,
    real_name text,
    status text not null default 'review_required',
    created_at text not null
);

create table if not exists analysis_runs (
    id text primary key,
    org_id text not null,
    application_id text not null,
    mode text not null,
    status text not null default 'completed',
    incomplete_reason text,
    executive_summary text,
    match_score real,
    evidence_confidence real,
    document_integrity real,
    low_confidence integer default 0,
    human_review_required integer default 0,
    human_review_reasons text default '[]',
    score_breakdown text,
    requirement_analysis text,
    claim_consistency text,
    career_trajectory text,
    adaptability text,
    capability_graph text,
    integrity_report text,
    interview_questions text,
    created_at text not null
);

create table if not exists recruiter_decisions (
    id text primary key,
    org_id text not null,
    application_id text not null,
    original_status text not null,
    decision text not null,
    final_status text not null,
    reason text,
    recruiter_id text,
    created_at text not null
);

create table if not exists ranking_snapshots (
    id text primary key,
    org_id text not null,
    job_id text not null,
    application_id text not null,
    analysis_run_id text,
    rank integer not null,
    match_score real not null,
    evidence_confidence real not null,
    document_integrity real not null,
    ranking_status text not null,
    ranking_version integer not null,
    created_at text not null
);

create table if not exists candidate_selections (
    id text primary key,
    org_id text not null,
    application_id text not null unique,
    recruiter_id text not null,
    selection_status text not null,
    selection_reason text,
    selected_at text not null
);

create table if not exists interview_questions (
    id text primary key,
    org_id text not null,
    application_id text not null,
    claim_id text,
    requirement_id text,
    question text not null,
    purpose text,
    evidence_gap text,
    verification_category text not null,
    expected_evidence text default '',
    priority integer default 1,
    status text not null default 'generated',
    recruiter_notes text,
    created_at text not null,
    updated_at text not null
);

create table if not exists interview_verifications (
    id text primary key,
    org_id text not null,
    application_id text not null,
    claim_id text,
    question_id text not null,
    recruiter_id text not null,
    verification_status text not null,
    verification_notes text default '',
    verified_at text not null,
    created_at text not null
);

create table if not exists audit_log (
    id text primary key,
    org_id text not null,
    action text not null,
    object_type text not null,
    object_id text not null,
    user_id text not null,
    metadata_json text default '{}',
    created_at text not null
);

create index if not exists idx_jobs_org on jobs(org_id);
create index if not exists idx_resumes_org on resumes(org_id);
create index if not exists idx_applications_org_job on applications(org_id, job_id);
create index if not exists idx_analysis_runs_application on analysis_runs(application_id);
create index if not exists idx_audit_org on audit_log(org_id);
create index if not exists idx_questions_app on interview_questions(application_id);
create index if not exists idx_verifications_app on interview_verifications(application_id);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return str(uuid.uuid4())


class SQLiteStore:
    mode = "sqlite"

    def __init__(self, settings: Settings):
        self.path = Path(settings.effective_sqlite_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    # ---- organizations / profiles -------------------------------------------
    def create_organization(self, name: str) -> str:
        org_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                "insert into organizations (id, name, created_at) values (?, ?, ?)",
                (org_id, name, _now()),
            )
        return org_id

    def ensure_profile(self, user_id: str, email: str, display_name: str = "") -> None:
        with self._conn() as conn:
            conn.execute(
                "insert or ignore into profiles (id, email, display_name, created_at) values (?, ?, ?, ?)",
                (user_id, email, display_name, _now()),
            )

    def create_user_with_password(self, email: str, password_hash: str, password_salt: str, display_name: str = "") -> str:
        user_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                """insert into profiles (id, email, display_name, password_hash, password_salt, created_at)
                   values (?, ?, ?, ?, ?, ?)""",
                (user_id, email, display_name, password_hash, password_salt, _now()),
            )
        return user_id

    def get_profile_by_email(self, email: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute("select * from profiles where email=?", (email,)).fetchone()

    def get_profile(self, user_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute("select * from profiles where id=?", (user_id,)).fetchone()

    def add_org_member(self, org_id: str, user_id: str, role: str = "owner") -> None:
        with self._conn() as conn:
            conn.execute(
                "insert into organization_members (id, org_id, user_id, role, created_at) values (?, ?, ?, ?, ?)",
                (_new_id(), org_id, user_id, role, _now()),
            )

    def list_orgs_for_user(self, user_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """select o.* from organizations o
                   join organization_members m on m.org_id = o.id
                   where m.user_id = ? order by o.created_at asc""",
                (user_id,),
            ).fetchall()

    def is_org_member(self, org_id: str, user_id: str) -> bool:
        with self._conn() as conn:
            row = conn.execute(
                "select 1 from organization_members where org_id=? and user_id=?",
                (org_id, user_id),
            ).fetchone()
            return row is not None

    # ---- jobs -----------------------------------------------------------------
    def create_job(self, org_id: str, title: str, department: str, location: str,
                    employment_type: str, description: str, experience_requirement: str) -> str:
        job_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                """insert into jobs (id, org_id, title, department, location, employment_type,
                   description, experience_requirement, created_at)
                   values (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (job_id, org_id, title, department, location, employment_type,
                 description, experience_requirement, _now()),
            )
        return job_id

    def set_job_requirements(self, job_id: str, requirements_json: str, experience_years_min: float | None = None) -> None:
        with self._conn() as conn:
            # Requirements changing invalidates the meaning of any ranking
            # computed against the old criteria (spec update §12) — bump
            # the version so a fresh ranking is generated rather than
            # silently compared against a now-stale one.
            conn.execute(
                """update jobs set requirements_json=?, requirements_analyzed=1,
                   experience_years_min=?, ranking_version=ranking_version+1 where id=?""",
                (requirements_json, experience_years_min, job_id),
            )

    def get_job(self, org_id: str, job_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "select * from jobs where id=? and org_id=?", (job_id, org_id)
            ).fetchone()

    def list_jobs(self, org_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "select * from jobs where org_id=? order by created_at desc", (org_id,)
            ).fetchall()

    def delete_job(self, org_id: str, job_id: str) -> bool:
        with self._conn() as conn:
            apps = conn.execute("select id from applications where job_id=? and org_id=?", (job_id, org_id)).fetchall()
            for app in apps:
                app_id = app["id"]
                conn.execute("delete from analysis_runs where application_id=? and org_id=?", (app_id, org_id))
                conn.execute("delete from candidate_selections where application_id=? and org_id=?", (app_id, org_id))
                conn.execute("delete from recruiter_decisions where application_id=? and org_id=?", (app_id, org_id))
            conn.execute("delete from applications where job_id=? and org_id=?", (job_id, org_id))
            conn.execute("delete from ranking_snapshots where job_id=? and org_id=?", (job_id, org_id))
            cur = conn.execute("delete from jobs where id=? and org_id=?", (job_id, org_id))
            return cur.rowcount > 0

    # ---- candidates / resumes / applications ----------------------------------
    def create_candidate(self, org_id: str, display_name: str = "", email: str = "") -> str:
        candidate_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                "insert into candidates (id, org_id, display_name, email, created_at) values (?, ?, ?, ?, ?)",
                (candidate_id, org_id, display_name, email, _now()),
            )
        return candidate_id

    def create_resume(self, org_id: str, candidate_id: str, file_name: str, storage_path: str) -> str:
        resume_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                """insert into resumes (id, org_id, candidate_id, file_name, storage_path, status, created_at)
                   values (?, ?, ?, ?, ?, 'uploaded', ?)""",
                (resume_id, org_id, candidate_id, file_name, storage_path, _now()),
            )
        return resume_id

    def update_resume_status(self, resume_id: str, status: str, page_count: int | None = None,
                              failure_reason: str | None = None) -> None:
        with self._conn() as conn:
            conn.execute(
                "update resumes set status=?, page_count=coalesce(?, page_count), failure_reason=? where id=?",
                (status, page_count, failure_reason, resume_id),
            )

    def get_resume(self, org_id: str, resume_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "select * from resumes where id=? and org_id=?", (resume_id, org_id)
            ).fetchone()

    def create_application(self, org_id: str, job_id: str, candidate_id: str, resume_id: str,
                            display_label: str, real_name: str = "") -> str:
        application_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                """insert into applications (id, org_id, job_id, candidate_id, resume_id,
                   display_label, real_name, status, created_at)
                   values (?, ?, ?, ?, ?, ?, ?, 'review_required', ?)""",
                (application_id, org_id, job_id, candidate_id, resume_id, display_label, real_name, _now()),
            )
        return application_id

    def next_display_label(self, org_id: str, job_id: str) -> str:
        with self._conn() as conn:
            row = conn.execute(
                "select count(*) as n from applications where org_id=? and job_id=?",
                (org_id, job_id),
            ).fetchone()
            n = (row["n"] if row else 0) + 1
            return f"Candidate #{n:03d}"

    def get_application(self, org_id: str, application_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "select * from applications where id=? and org_id=?", (application_id, org_id)
            ).fetchone()

    def list_applications_for_job(self, org_id: str, job_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "select * from applications where org_id=? and job_id=? order by created_at asc",
                (org_id, job_id),
            ).fetchall()

    def update_application_status(self, application_id: str, status: str) -> None:
        with self._conn() as conn:
            conn.execute("update applications set status=? where id=?", (status, application_id))

    # ---- analysis runs ----------------------------------------------------------
    def save_analysis_run(self, org_id: str, application_id: str, data: dict) -> str:
        run_id = _new_id()
        with self._conn() as conn:
            conn.execute(
                """insert into analysis_runs (
                    id, org_id, application_id, mode, status, incomplete_reason,
                    executive_summary, match_score, evidence_confidence, document_integrity,
                    low_confidence, human_review_required, human_review_reasons,
                    score_breakdown, requirement_analysis, claim_consistency,
                    career_trajectory, adaptability, capability_graph, integrity_report,
                    interview_questions, created_at
                ) values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run_id, org_id, application_id, data["mode"], data["status"], data.get("incomplete_reason"),
                    data.get("executive_summary"), data.get("match_score"), data.get("evidence_confidence"),
                    data.get("document_integrity"), int(data.get("low_confidence", False)),
                    int(data.get("human_review_required", False)),
                    json.dumps(data.get("human_review_reasons", [])),
                    json.dumps(data.get("score_breakdown")), json.dumps(data.get("requirement_analysis")),
                    json.dumps(data.get("claim_consistency")), json.dumps(data.get("career_trajectory")),
                    json.dumps(data.get("adaptability")), json.dumps(data.get("capability_graph")),
                    json.dumps(data.get("integrity_report")), json.dumps(data.get("interview_questions")),
                    _now(),
                ),
            )
        return run_id

    def get_latest_analysis(self, org_id: str, application_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                """select * from analysis_runs where org_id=? and application_id=?
                   order by created_at desc limit 1""",
                (org_id, application_id),
            ).fetchone()

    # ---- recruiter decisions ------------------------------------------------------
    def save_decision(self, org_id: str, application_id: str, original_status: str,
                       decision: str, final_status: str, reason: str | None, recruiter_id: str) -> sqlite3.Row:
        decision_id = _new_id()
        created_at = _now()
        with self._conn() as conn:
            conn.execute(
                """insert into recruiter_decisions (id, org_id, application_id, original_status,
                   decision, final_status, reason, recruiter_id, created_at)
                   values (?,?,?,?,?,?,?,?,?)""",
                (decision_id, org_id, application_id, original_status, decision, final_status,
                 reason, recruiter_id, created_at),
            )
            conn.execute("update applications set status=? where id=?", (final_status, application_id))
            row = conn.execute(
                "select * from recruiter_decisions where id=?", (decision_id,)
            ).fetchone()
        return row

    # ---- ranking ------------------------------------------------------------------
    def get_ranking_version(self, org_id: str, job_id: str) -> int:
        with self._conn() as conn:
            row = conn.execute(
                "select ranking_version from jobs where id=? and org_id=?", (job_id, org_id)
            ).fetchone()
            return row["ranking_version"] if row else 1

    def save_ranking_snapshot(self, org_id: str, job_id: str, ranking_version: int, rows: list[dict]) -> None:
        """Persists one immutable snapshot row per candidate for this
        ranking computation — spec update §12: ranking history is never
        silently overwritten, a new job-requirements version produces a
        new set of snapshot rows tagged with the version that produced
        them, and old ones stay exactly as they were."""
        created_at = _now()
        with self._conn() as conn:
            for r in rows:
                conn.execute(
                    """insert into ranking_snapshots (id, org_id, job_id, application_id,
                       analysis_run_id, rank, match_score, evidence_confidence, document_integrity,
                       ranking_status, ranking_version, created_at)
                       values (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        _new_id(), org_id, job_id, r["application_id"], r.get("analysis_run_id"),
                        r["rank"], r["match_score"], r["evidence_confidence"], r["document_integrity"],
                        r["ranking_status"], ranking_version, created_at,
                    ),
                )

    def get_ranking_history(self, org_id: str, job_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                """select * from ranking_snapshots where org_id=? and job_id=?
                   order by ranking_version desc, rank asc""",
                (org_id, job_id),
            ).fetchall()

    # ---- recruiter selections (separate from AI rank/score and from decisions) ----
    def upsert_selection(self, org_id: str, application_id: str, recruiter_id: str,
                          selection_status: str, selection_reason: str | None) -> sqlite3.Row:
        with self._conn() as conn:
            existing = conn.execute(
                "select id from candidate_selections where application_id=?", (application_id,)
            ).fetchone()
            selected_at = _now()
            if existing:
                conn.execute(
                    """update candidate_selections set recruiter_id=?, selection_status=?,
                       selection_reason=?, selected_at=? where application_id=?""",
                    (recruiter_id, selection_status, selection_reason, selected_at, application_id),
                )
            else:
                conn.execute(
                    """insert into candidate_selections (id, org_id, application_id, recruiter_id,
                       selection_status, selection_reason, selected_at) values (?,?,?,?,?,?,?)""",
                    (_new_id(), org_id, application_id, recruiter_id, selection_status, selection_reason, selected_at),
                )
            return conn.execute(
                "select * from candidate_selections where application_id=?", (application_id,)
            ).fetchone()

    def get_selection(self, org_id: str, application_id: str) -> sqlite3.Row | None:
        with self._conn() as conn:
            return conn.execute(
                "select * from candidate_selections where org_id=? and application_id=?",
                (org_id, application_id),
            ).fetchone()

    def list_selections_for_job(self, org_id: str, job_id: str) -> dict[str, sqlite3.Row]:
        with self._conn() as conn:
            rows = conn.execute(
                """select cs.* from candidate_selections cs
                   join applications a on a.id = cs.application_id
                   where cs.org_id=? and a.job_id=?""",
                (org_id, job_id),
            ).fetchall()
            return {r["application_id"]: r for r in rows}

    # ---- audit log ----------------------------------------------------------------
    def append_audit(self, org_id: str, action: str, object_type: str, object_id: str,
                      user_id: str, metadata: dict) -> None:
        with self._conn() as conn:
            conn.execute(
                """insert into audit_log (id, org_id, action, object_type, object_id, user_id,
                   metadata_json, created_at) values (?,?,?,?,?,?,?,?)""",
                (_new_id(), org_id, action, object_type, object_id, user_id, json.dumps(metadata), _now()),
            )

    def list_audit(self, org_id: str, object_type: str | None = None, object_id: str | None = None) -> list[sqlite3.Row]:
        query = "select * from audit_log where org_id=?"
        params: list = [org_id]
        if object_type:
            query += " and object_type=?"
            params.append(object_type)
        if object_id:
            query += " and object_id=?"
            params.append(object_id)
        query += " order by created_at desc"
        with self._conn() as conn:
            return conn.execute(query, params).fetchall()

    # ---- interview verification engine -------------------------------------------
    def save_verification_questions(self, org_id: str, application_id: str, questions: list) -> None:
        with self._conn() as conn:
            for q in questions:
                q_id = getattr(q, "id", None) or _new_id()
                conn.execute(
                    """insert or replace into interview_questions
                       (id, org_id, application_id, claim_id, requirement_id, question, purpose,
                        evidence_gap, verification_category, expected_evidence, priority, status,
                        recruiter_notes, created_at, updated_at)
                       values (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        q_id, org_id, application_id,
                        getattr(q, "claim_id", None), getattr(q, "requirement_id", None),
                        q.question, q.purpose, q.evidence_gap,
                        q.verification_category.value if hasattr(q.verification_category, "value") else str(q.verification_category),
                        q.expected_evidence or "", getattr(q, "priority", 1),
                        q.status.value if hasattr(q.status, "value") else str(q.status),
                        getattr(q, "recruiter_notes", None),
                        getattr(q, "created_at", _now()), _now(),
                    ),
                )

    def list_verification_questions(self, org_id: str, application_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "select * from interview_questions where org_id=? and application_id=? order by priority asc, created_at asc",
                (org_id, application_id),
            ).fetchall()

    def update_verification_question(self, org_id: str, question_id: str, status: str | None = None, recruiter_notes: str | None = None) -> sqlite3.Row | None:
        with self._conn() as conn:
            if status is not None:
                conn.execute(
                    "update interview_questions set status=?, updated_at=? where id=? and org_id=?",
                    (status, _now(), question_id, org_id),
                )
            if recruiter_notes is not None:
                conn.execute(
                    "update interview_questions set recruiter_notes=?, updated_at=? where id=? and org_id=?",
                    (recruiter_notes, _now(), question_id, org_id),
                )
            return conn.execute("select * from interview_questions where id=? and org_id=?", (question_id, org_id)).fetchone()

    def save_verification_record(self, org_id: str, application_id: str, claim_id: str | None, question_id: str, recruiter_id: str, status: str, notes: str = "") -> sqlite3.Row:
        rec_id = _new_id()
        now_str = _now()
        with self._conn() as conn:
            conn.execute(
                """insert into interview_verifications
                   (id, org_id, application_id, claim_id, question_id, recruiter_id, verification_status, verification_notes, verified_at, created_at)
                   values (?,?,?,?,?,?,?,?,?,?)""",
                (rec_id, org_id, application_id, claim_id, question_id, recruiter_id, status, notes, now_str, now_str),
            )
            # Update question status to verified/not_verified
            q_status = "verified" if status in ("verified", "partially_verified") else "not_verified"
            conn.execute(
                "update interview_questions set status=?, recruiter_notes=?, updated_at=? where id=? and org_id=?",
                (q_status, notes, now_str, question_id, org_id),
            )
            return conn.execute("select * from interview_verifications where id=?", (rec_id,)).fetchone()

    def list_verification_records(self, org_id: str, application_id: str) -> list[sqlite3.Row]:
        with self._conn() as conn:
            return conn.execute(
                "select * from interview_verifications where org_id=? and application_id=? order by created_at desc",
                (org_id, application_id),
            ).fetchall()

