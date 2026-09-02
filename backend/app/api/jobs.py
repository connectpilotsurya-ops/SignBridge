from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import OrgContext, org_context_dep
from app.llm.client import get_llm_client
from app.persistence.client import get_store
from app.schemas.candidate import CandidateRow
from app.schemas.enums import CandidateStatus, ResumeStatus
from app.schemas.job import JobCreate, JobOut, JobSummary
from app.schemas.ranking import JobRankingResponse
from app.schemas.requirement import JobRequirement
from app.services.analysis_view import load_candidate_analysis
from app.services.ranking_view import build_job_ranking

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _job_row_to_out(row) -> JobOut:
    reqs_raw = json.loads(row["requirements_json"] or "[]")
    return JobOut(
        id=row["id"],
        org_id=row["org_id"],
        title=row["title"],
        department=row["department"] or "",
        location=row["location"] or "",
        employment_type=row["employment_type"] or "full_time",
        description=row["description"],
        experience_requirement=row["experience_requirement"] or "",
        requirements=[JobRequirement.model_validate(r) for r in reqs_raw],
        requirements_analyzed=bool(row["requirements_analyzed"]),
        experience_years_min=row["experience_years_min"] if "experience_years_min" in row.keys() else None,
        created_at=row["created_at"],
    )


@router.post("", response_model=JobOut)
def create_job(body: JobCreate, ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    job_id = store.create_job(
        ctx.org_id, body.title, body.department, body.location,
        body.employment_type, body.description, body.experience_requirement,
    )
    store.append_audit(ctx.org_id, "job.created", "job", job_id, ctx.user.user_id, {"title": body.title})
    return _job_row_to_out(store.get_job(ctx.org_id, job_id))


@router.get("", response_model=list[JobSummary])
def list_jobs(ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    jobs = store.list_jobs(ctx.org_id)
    summaries = []
    for job in jobs:
        apps = store.list_applications_for_job(ctx.org_id, job["id"])
        review_count = sum(1 for a in apps if a["status"] == "review_required")
        best = None
        for a in apps:
            run = store.get_latest_analysis(ctx.org_id, a["id"])
            if run and run["match_score"] is not None:
                if best is None or run["match_score"] > best:
                    best = run["match_score"]
        last_analysis = None
        for a in apps:
            run = store.get_latest_analysis(ctx.org_id, a["id"])
            if run:
                if last_analysis is None or run["created_at"] > last_analysis:
                    last_analysis = run["created_at"]
        summaries.append(
            JobSummary(
                id=job["id"], title=job["title"], candidate_count=len(apps),
                last_analysis_at=last_analysis, top_candidate_score=best,
                review_required_count=review_count,
            )
        )
    return summaries


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    row = store.get_job(ctx.org_id, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return _job_row_to_out(row)


@router.post("/{job_id}/analyze", response_model=JobOut)
def analyze_job_requirements(job_id: str, ctx: OrgContext = Depends(org_context_dep)):
    """Spec §8: LLM extracts must-have/preferred requirements from the JD.
    Never infers requirements not present in the text (enforced by the
    mock's vocabulary-only matching and, in real mode, the system prompt
    in app/llm/prompts.py)."""
    store = get_store()
    row = store.get_job(ctx.org_id, job_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Job not found")

    llm = get_llm_client()
    result = llm.extract_requirements(row["description"], row["experience_requirement"] or "")
    reqs_json = json.dumps([r.model_dump(mode="json") for r in result.requirements])
    store.set_job_requirements(job_id, reqs_json, result.experience_years_min)
    store.append_audit(
        ctx.org_id, "job.requirements_extracted", "job", job_id, ctx.user.user_id,
        {"count": len(result.requirements), "mode": llm.mode},
    )
    return _job_row_to_out(store.get_job(ctx.org_id, job_id))


@router.get("/{job_id}/ranking", response_model=JobRankingResponse)
def get_job_ranking(job_id: str, ctx: OrgContext = Depends(org_context_dep)):
    """Spec update §17: the primary candidate dashboard. Every analyzed
    candidate is ranked by evidence-backed match_score (never a subset,
    never an AI-picked shortlist) — the deterministic ranking engine
    (app/scoring/ranking.py) sorts and labels; this endpoint never filters
    anyone out. Recruiters decide who advances via the separate
    /selection endpoint below, which this response only reflects."""
    ranking = build_job_ranking(ctx.org_id, job_id)
    if ranking is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return ranking


@router.get("/{job_id}/ranking/history")
def get_job_ranking_history(job_id: str, ctx: OrgContext = Depends(org_context_dep)):
    """Spec update §12: past ranking_version snapshots are preserved, not
    overwritten, whenever job requirements (and therefore the ranking)
    change — this returns every snapshot ever computed for this job."""
    store = get_store()
    if store.get_job(ctx.org_id, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")
    rows = store.get_ranking_history(ctx.org_id, job_id)
    return [
        {
            "application_id": r["application_id"],
            "rank": r["rank"],
            "match_score": r["match_score"],
            "evidence_confidence": r["evidence_confidence"],
            "document_integrity": r["document_integrity"],
            "ranking_status": r["ranking_status"],
            "ranking_version": r["ranking_version"],
            "created_at": r["created_at"],
        }
        for r in rows
    ]


@router.get("/{job_id}/candidates", response_model=list[CandidateRow])
def list_job_candidates(job_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    """Spec §32's candidate table. `blind=true` shows "Candidate #NNN"
    instead of the real name (spec §30) — the underlying record is
    untouched either way, this only changes what this response exposes."""
    store = get_store()
    if store.get_job(ctx.org_id, job_id) is None:
        raise HTTPException(status_code=404, detail="Job not found")

    rows = []
    for application in store.list_applications_for_job(ctx.org_id, job_id):
        resume = store.get_resume(ctx.org_id, application["resume_id"]) if application["resume_id"] else None
        analysis = load_candidate_analysis(ctx.org_id, application["id"], blind_mode=blind)
        if analysis is None:
            rows.append(
                CandidateRow(
                    application_id=application["id"],
                    display_label=application["display_label"],
                    match_score=0, evidence_confidence=0, document_integrity=0,
                    status=CandidateStatus.REVIEW_REQUIRED,
                    resume_status=ResumeStatus(resume["status"]) if resume else ResumeStatus.UPLOADED,
                )
            )
            continue
        strengths = [a.requirement for a in analysis.requirement_analysis if a.status.value in ("exact_match", "equivalent_match")][:3]
        gaps = [a.requirement for a in analysis.requirement_analysis if a.status.value in ("not_evidenced", "potential_gaming")][:3]
        rows.append(
            CandidateRow(
                application_id=application["id"],
                display_label=analysis.display_label,
                match_score=analysis.scores.match_score,
                evidence_confidence=analysis.scores.evidence_confidence,
                document_integrity=analysis.scores.document_integrity,
                status=analysis.status,
                top_strengths=strengths,
                major_gaps=gaps,
                resume_status=ResumeStatus(resume["status"]) if resume else ResumeStatus.COMPLETED,
            )
        )
    return rows
