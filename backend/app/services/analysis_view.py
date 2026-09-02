"""Reconstructs the full CandidateAnalysis Pydantic object from the JSON
columns saved by upload_service.process_resume_upload. This is the single
place that deserializes an analysis_runs row — every /api/applications/*
endpoint goes through it so the shape can never drift between endpoints."""
from __future__ import annotations

import json

from app.persistence.client import get_store
from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.candidate import CandidateAnalysis
from app.schemas.career import AdaptabilityIndicator, CareerTrajectory
from app.schemas.enums import CandidateStatus
from app.schemas.graph import CapabilityGraph
from app.schemas.integrity import IntegrityReport
from app.schemas.interview import InterviewQuestion
from app.schemas.score import CandidateScores, ScoreBreakdown


def load_candidate_analysis(org_id: str, application_id: str, blind_mode: bool = False) -> CandidateAnalysis | None:
    store = get_store()
    application = store.get_application(org_id, application_id)
    if application is None:
        return None
    run = store.get_latest_analysis(org_id, application_id)
    if run is None:
        return None

    breakdown = ScoreBreakdown.model_validate(json.loads(run["score_breakdown"] or "{}"))
    scores = CandidateScores(
        match_score=run["match_score"] or 0,
        evidence_confidence=run["evidence_confidence"] or 0,
        document_integrity=run["document_integrity"] or 0,
        breakdown=breakdown,
        low_confidence=bool(run["low_confidence"]),
    )

    label = application["display_label"]
    display_label = label if blind_mode else (application["real_name"] or label)

    return CandidateAnalysis(
        application_id=application["id"],
        display_label=display_label,
        blind_mode=blind_mode,
        scores=scores,
        status=CandidateStatus(application["status"]),
        executive_summary=run["executive_summary"] or "",
        requirement_analysis=[RequirementAssessment.model_validate(a) for a in json.loads(run["requirement_analysis"] or "[]")],
        claim_consistency=[ClaimEvidenceConsistency.model_validate(c) for c in json.loads(run["claim_consistency"] or "[]")],
        career_trajectory=CareerTrajectory.model_validate(json.loads(run["career_trajectory"] or '{"points":[],"summary":""}')),
        adaptability=AdaptabilityIndicator.model_validate(json.loads(run["adaptability"] or '{"level":"low","technology_transitions":0,"role_transitions":0,"explanation":""}')),
        capability_graph=CapabilityGraph.model_validate(json.loads(run["capability_graph"] or '{"nodes":[],"edges":[]}')),
        integrity=IntegrityReport.model_validate(json.loads(run["integrity_report"] or '{"category":"normal","score":100,"flags":[],"suppressed_terms":[]}')),
        interview_questions=[InterviewQuestion.model_validate(q) for q in json.loads(run["interview_questions"] or "[]")],
        human_review_required=bool(run["human_review_required"]),
        human_review_reasons=json.loads(run["human_review_reasons"] or "[]"),
        analysis_mode=run["mode"],
        analysis_incomplete=run["status"] == "incomplete",
        incomplete_reason=run["incomplete_reason"],
        created_at=run["created_at"],
    )
