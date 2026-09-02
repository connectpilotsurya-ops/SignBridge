"""Ties together resume upload -> storage -> the analysis pipeline ->
persistence. Runs synchronously — spec §42 explicitly says not to build
unnecessary microservices for the MVP, and at hackathon scale (one
recruiter uploading a batch of resumes) a background queue buys nothing
but complexity. The frontend shows the processing states from spec §9
(UPLOADED -> PARSING -> ANALYZING -> COMPLETED/FAILED/REVIEW_REQUIRED)
by polling GET /api/resumes/{id}, which reflects each state this
function writes as it goes."""
from __future__ import annotations

import json

from app.llm.base import LLMClient
from app.persistence.client import get_file_storage, get_store
from app.schemas.requirement import JobRequirement
from app.services.analysis_pipeline import run_analysis


def process_resume_upload(
    org_id: str,
    user_id: str,
    job_row,
    file_bytes: bytes,
    file_name: str,
    candidate_name: str,
    candidate_email: str,
    llm: LLMClient,
) -> str:
    store = get_store()
    storage = get_file_storage()

    candidate_id = store.create_candidate(org_id, candidate_name, candidate_email)
    storage_path = storage.save(org_id, file_bytes)
    resume_id = store.create_resume(org_id, candidate_id, file_name, storage_path)

    label = store.next_display_label(org_id, job_row["id"])
    application_id = store.create_application(org_id, job_row["id"], candidate_id, resume_id, label, candidate_name)
    store.append_audit(org_id, "resume.uploaded", "resume", resume_id, user_id, {"file_name": file_name})

    store.update_resume_status(resume_id, "parsing")
    requirements = [JobRequirement.model_validate(r) for r in json.loads(job_row["requirements_json"] or "[]")]

    store.update_resume_status(resume_id, "analyzing")
    experience_years_min = (
        job_row["experience_years_min"] if "experience_years_min" in job_row.keys() else None
    )
    result = run_analysis(
        llm=llm,
        job_title=job_row["title"],
        requirements=requirements,
        experience_years_min=experience_years_min,
        resume_bytes=file_bytes,
        candidate_label=label,
    )

    final_resume_status = (
        "failed" if result.analysis_incomplete
        else "review_required" if result.human_review_required
        else "completed"
    )
    store.update_resume_status(resume_id, final_resume_status, page_count=result.page_count,
                                failure_reason=result.incomplete_reason)

    store.save_analysis_run(
        org_id, application_id,
        {
            "mode": result.analysis_mode,
            "status": "incomplete" if result.analysis_incomplete else "completed",
            "incomplete_reason": result.incomplete_reason,
            "executive_summary": result.executive_summary,
            "match_score": result.scores.match_score,
            "evidence_confidence": result.scores.evidence_confidence,
            "document_integrity": result.scores.document_integrity,
            "low_confidence": result.scores.low_confidence,
            "human_review_required": result.human_review_required,
            "human_review_reasons": result.human_review_reasons,
            "score_breakdown": result.scores.breakdown.model_dump(mode="json"),
            "requirement_analysis": [a.model_dump(mode="json") for a in result.requirement_analysis],
            "claim_consistency": [c.model_dump(mode="json") for c in result.claim_consistency],
            "career_trajectory": result.career_trajectory.model_dump(mode="json"),
            "adaptability": result.adaptability.model_dump(mode="json"),
            "capability_graph": result.capability_graph.model_dump(mode="json"),
            "integrity_report": result.integrity.model_dump(mode="json"),
            "interview_questions": [q.model_dump(mode="json") for q in result.interview_questions],
            "status_label": result.status.value,
        },
    )
    store.update_application_status(application_id, result.status.value)
    store.append_audit(
        org_id, "analysis.completed", "application", application_id, user_id,
        {"match_score": result.scores.match_score, "status": result.status.value, "mode": result.analysis_mode},
    )
    return application_id
