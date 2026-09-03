"""
Real-mode persistence against Supabase Postgres — spec §4/§6/§7.

Method-for-method mirror of SQLiteStore's surface so app/services/*.py
never has to branch on which store it's talking to. This targets the
schema in db/schema.sql using the `supabase-py` client with the service
role key (server-side only — spec §41 "no API secrets in frontend").

Honesty note: there is no live Supabase project reachable from this
sandbox, so this adapter is written correctly against the documented
supabase-py API and the schema above, but has not been exercised against
a real database. Run the backend test suite against it once you've
applied db/schema.sql to your own project and filled in .env — treat it
as reviewed-but-unverified code, the same way you'd treat a teammate's PR
you haven't pulled and run yet.
"""
from __future__ import annotations

import json

from app.config import Settings


class SupabaseStore:
    mode = "supabase"

    def __init__(self, settings: Settings):
        from supabase import create_client

        self._client = create_client(settings.supabase_url, settings.supabase_service_role_key)

    # ---- organizations / profiles -------------------------------------------
    def create_organization(self, name: str) -> str:
        res = self._client.table("organizations").insert({"name": name}).execute()
        return res.data[0]["id"]

    def ensure_profile(self, user_id: str, email: str, display_name: str = "") -> None:
        self._client.table("profiles").upsert(
            {"id": user_id, "email": email, "display_name": display_name}
        ).execute()

    def add_org_member(self, org_id: str, user_id: str, role: str = "owner") -> None:
        self._client.table("organization_members").insert(
            {"org_id": org_id, "user_id": user_id, "role": role}
        ).execute()

    def is_org_member(self, org_id: str, user_id: str) -> bool:
        res = (
            self._client.table("organization_members")
            .select("id")
            .eq("org_id", org_id)
            .eq("user_id", user_id)
            .execute()
        )
        return len(res.data) > 0

    # ---- jobs -----------------------------------------------------------------
    def create_job(self, org_id, title, department, location, employment_type, description, experience_requirement) -> str:
        res = (
            self._client.table("jobs")
            .insert(
                {
                    "org_id": org_id,
                    "title": title,
                    "department": department,
                    "location": location,
                    "employment_type": employment_type,
                    "description": description,
                    "experience_requirement": experience_requirement,
                }
            )
            .execute()
        )
        return res.data[0]["id"]

    def set_job_requirements(self, job_id: str, requirements_json: str, experience_years_min: float | None = None) -> None:
        requirements = json.loads(requirements_json)
        self._client.table("job_requirements").delete().eq("job_id", job_id).execute()
        if requirements:
            org_id = self._client.table("jobs").select("org_id").eq("id", job_id).execute().data[0]["org_id"]
            rows = [{**r, "job_id": job_id, "org_id": org_id} for r in requirements]
            self._client.table("job_requirements").insert(rows).execute()
        # Spec update §12: requirements changing means the ranking model
        # changed, so bump ranking_version — ranking_snapshots tagged with
        # the old version stay exactly as they were, never overwritten.
        current = self._client.table("jobs").select("ranking_version").eq("id", job_id).execute()
        next_version = ((current.data[0].get("ranking_version") or 1) + 1) if current.data else 1
        self._client.table("jobs").update(
            {
                "requirements_analyzed": True,
                "experience_years_min": experience_years_min,
                "ranking_version": next_version,
            }
        ).eq("id", job_id).execute()

    def get_job(self, org_id: str, job_id: str):
        res = self._client.table("jobs").select("*").eq("id", job_id).eq("org_id", org_id).execute()
        if not res.data:
            return None
        job = res.data[0]
        reqs = self._client.table("job_requirements").select("*").eq("job_id", job_id).execute()
        job["requirements_json"] = json.dumps(reqs.data)
        return job

    def list_jobs(self, org_id: str):
        res = self._client.table("jobs").select("*").eq("org_id", org_id).order("created_at", desc=True).execute()
        return res.data

    def delete_job(self, org_id: str, job_id: str) -> bool:
        res = self._client.table("jobs").delete().eq("id", job_id).eq("org_id", org_id).execute()
        return len(res.data) > 0

    # ---- candidates / resumes / applications ----------------------------------
    def create_candidate(self, org_id: str, display_name: str = "", email: str = "") -> str:
        res = self._client.table("candidates").insert(
            {"org_id": org_id, "display_name": display_name, "email": email}
        ).execute()
        return res.data[0]["id"]

    def create_resume(self, org_id: str, candidate_id: str, file_name: str, storage_path: str) -> str:
        res = self._client.table("resumes").insert(
            {"org_id": org_id, "candidate_id": candidate_id, "file_name": file_name, "storage_path": storage_path}
        ).execute()
        return res.data[0]["id"]

    def update_resume_status(self, resume_id: str, status: str, page_count=None, failure_reason=None) -> None:
        patch = {"status": status}
        if page_count is not None:
            patch["page_count"] = page_count
        self._client.table("resumes").update(patch).eq("id", resume_id).execute()

    def get_resume(self, org_id: str, resume_id: str):
        res = self._client.table("resumes").select("*").eq("id", resume_id).eq("org_id", org_id).execute()
        return res.data[0] if res.data else None

    def create_application(self, org_id, job_id, candidate_id, resume_id, display_label, real_name="") -> str:
        res = self._client.table("applications").insert(
            {
                "org_id": org_id, "job_id": job_id, "candidate_id": candidate_id,
                "resume_id": resume_id, "display_label": display_label,
            }
        ).execute()
        return res.data[0]["id"]

    def next_display_label(self, org_id: str, job_id: str) -> str:
        res = self._client.table("applications").select("id", count="exact").eq("org_id", org_id).eq("job_id", job_id).execute()
        n = (res.count or 0) + 1
        return f"Candidate #{n:03d}"

    def get_application(self, org_id: str, application_id: str):
        res = self._client.table("applications").select("*").eq("id", application_id).eq("org_id", org_id).execute()
        return res.data[0] if res.data else None

    def list_applications_for_job(self, org_id: str, job_id: str):
        res = self._client.table("applications").select("*").eq("org_id", org_id).eq("job_id", job_id).order("created_at").execute()
        return res.data

    def update_application_status(self, application_id: str, status: str) -> None:
        self._client.table("applications").update({"status": status}).eq("id", application_id).execute()

    # ---- analysis runs ----------------------------------------------------------
    def save_analysis_run(self, org_id: str, application_id: str, data: dict) -> str:
        row = {
            "org_id": org_id, "application_id": application_id,
            "mode": data["mode"], "status": data["status"],
            "incomplete_reason": data.get("incomplete_reason"),
            "executive_summary": data.get("executive_summary"),
            "match_score": data.get("match_score"),
            "evidence_confidence": data.get("evidence_confidence"),
            "document_integrity": data.get("document_integrity"),
            "low_confidence": data.get("low_confidence", False),
            "human_review_required": data.get("human_review_required", False),
            "human_review_reasons": data.get("human_review_reasons", []),
            "score_breakdown": data.get("score_breakdown"),
            "requirement_analysis": data.get("requirement_analysis"),
            "claim_consistency": data.get("claim_consistency"),
            "career_trajectory": data.get("career_trajectory"),
            "adaptability": data.get("adaptability"),
            "capability_graph": data.get("capability_graph"),
            "integrity_report": data.get("integrity_report"),
            "interview_questions": data.get("interview_questions"),
        }
        res = self._client.table("analysis_runs").insert(row).execute()
        run_id = res.data[0]["id"]
        self._client.table("candidate_scores").upsert(
            {
                "application_id": application_id, "org_id": org_id,
                "match_score": data.get("match_score"),
                "evidence_confidence": data.get("evidence_confidence"),
                "document_integrity": data.get("document_integrity"),
                "status": data.get("status_label", "review_required"),
            }
        ).execute()
        return run_id

    def get_latest_analysis(self, org_id: str, application_id: str):
        res = (
            self._client.table("analysis_runs")
            .select("*")
            .eq("org_id", org_id)
            .eq("application_id", application_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return res.data[0] if res.data else None

    # ---- recruiter decisions ------------------------------------------------------
    def save_decision(self, org_id, application_id, original_status, decision, final_status, reason, recruiter_id):
        res = self._client.table("recruiter_decisions").insert(
            {
                "org_id": org_id, "application_id": application_id,
                "original_status": original_status, "decision": decision,
                "final_status": final_status, "reason": reason, "recruiter_id": recruiter_id,
            }
        ).execute()
        self._client.table("applications").update({"status": final_status}).eq("id", application_id).execute()
        return res.data[0]

    # ---- ranking ------------------------------------------------------------------
    def get_ranking_version(self, org_id: str, job_id: str) -> int:
        res = self._client.table("jobs").select("ranking_version").eq("id", job_id).eq("org_id", org_id).execute()
        if not res.data:
            return 1
        return res.data[0].get("ranking_version") or 1

    def save_ranking_snapshot(self, org_id: str, job_id: str, ranking_version: int, rows: list[dict]) -> None:
        """Spec update §12: one immutable row per candidate per ranking
        computation, tagged with the version that produced it — never
        updated in place, so past rankings stay exactly as computed even
        after job requirements (and therefore the model) change."""
        if not rows:
            return
        payload = [
            {
                "org_id": org_id,
                "job_id": job_id,
                "application_id": r["application_id"],
                "analysis_run_id": r.get("analysis_run_id"),
                "rank": r["rank"],
                "match_score": r["match_score"],
                "evidence_confidence": r["evidence_confidence"],
                "document_integrity": r["document_integrity"],
                "ranking_status": r["ranking_status"],
                "ranking_version": ranking_version,
            }
            for r in rows
        ]
        self._client.table("ranking_snapshots").insert(payload).execute()

    def get_ranking_history(self, org_id: str, job_id: str):
        res = (
            self._client.table("ranking_snapshots")
            .select("*")
            .eq("org_id", org_id)
            .eq("job_id", job_id)
            .order("ranking_version", desc=True)
            .order("rank")
            .execute()
        )
        return res.data

    # ---- recruiter selections (separate from AI rank/score and from decisions) ----
    def upsert_selection(self, org_id: str, application_id: str, recruiter_id: str,
                          selection_status: str, selection_reason: str | None):
        res = self._client.table("candidate_selections").upsert(
            {
                "org_id": org_id,
                "application_id": application_id,
                "recruiter_id": recruiter_id,
                "selection_status": selection_status,
                "selection_reason": selection_reason,
                "selected_at": "now()",
            },
            on_conflict="application_id",
        ).execute()
        if res.data:
            return res.data[0]
        return self.get_selection(org_id, application_id)

    def get_selection(self, org_id: str, application_id: str):
        res = (
            self._client.table("candidate_selections")
            .select("*")
            .eq("org_id", org_id)
            .eq("application_id", application_id)
            .execute()
        )
        return res.data[0] if res.data else None

    def list_selections_for_job(self, org_id: str, job_id: str) -> dict:
        app_ids = [a["id"] for a in self.list_applications_for_job(org_id, job_id)]
        if not app_ids:
            return {}
        res = (
            self._client.table("candidate_selections")
            .select("*")
            .eq("org_id", org_id)
            .in_("application_id", app_ids)
            .execute()
        )
        return {r["application_id"]: r for r in res.data}

    # ---- audit log ----------------------------------------------------------------
    def append_audit(self, org_id: str, action: str, object_type: str, object_id: str, user_id: str, metadata: dict) -> None:
        self._client.table("audit_log").insert(
            {
                "org_id": org_id, "action": action, "object_type": object_type,
                "object_id": object_id, "user_id": user_id, "metadata": metadata,
            }
        ).execute()

    def list_audit(self, org_id: str, object_type: str | None = None, object_id: str | None = None):
        q = self._client.table("audit_log").select("*").eq("org_id", org_id)
        if object_type:
            q = q.eq("object_type", object_type)
        if object_id:
            q = q.eq("object_id", object_id)
        return q.order("created_at", desc=True).execute().data
