"""
Tests for the AI Interview Verification Engine.
"""
from __future__ import annotations

import pytest
from app.services.verification_engine import (
    classify_evidence_level,
    analyze_candidate_verifications,
    generate_verification_questions_for_claim,
)
from app.schemas.enums import EvidenceGapType, VerificationCategory
from app.schemas.verification import CandidateClaim


def test_classify_evidence_level():
    assert classify_evidence_level(0.9, has_production=True, has_hidden=False) == "VERY_STRONG"
    assert classify_evidence_level(0.75, has_production=False, has_hidden=False) == "STRONG"
    assert classify_evidence_level(0.55, has_production=False, has_hidden=False) == "MODERATE"
    assert classify_evidence_level(0.3, has_production=False, has_hidden=False) == "WEAK"
    assert classify_evidence_level(0.1, has_production=False, has_hidden=False) == "INSUFFICIENT"
    assert classify_evidence_level(0.0, has_production=False, has_hidden=False) == "NONE"


def test_analyze_candidate_verifications_detects_gaps_and_generates_questions():
    reqs = [
        {
            "requirement": "Kubernetes",
            "status": "partial_match",
            "evidence": [{"text": "Used Kubernetes in a lab."}],
            "evidence_strength": 0.35,
        },
        {
            "requirement": "Docker",
            "status": "transferable",
            "evidence": [{"text": "Built Docker containers."}],
            "evidence_strength": 0.4,
        },
    ]

    claims, questions = analyze_candidate_verifications(
        org_id="org_test",
        application_id="app_test",
        requirement_assessments=reqs,
        integrity_report=None,
    )

    assert len(claims) == 2
    assert len(questions) >= 2

    k8s_claim = [c for c in claims if c.skill == "Kubernetes"][0]
    assert k8s_claim.verification_required is True
    assert EvidenceGapType.MISSING_PRODUCTION_EVIDENCE in k8s_claim.evidence_gaps
    assert EvidenceGapType.MISSING_OWNERSHIP_EVIDENCE in k8s_claim.evidence_gaps

    # Verify non-accusatory language
    assert "liar" not in k8s_claim.consistency_note.lower()
    assert "fake" not in k8s_claim.consistency_note.lower()
    assert "limited supporting evidence" in k8s_claim.consistency_note.lower()


def test_transferable_skills_question_generation():
    claim = CandidateClaim(
        id="claim_docker",
        claim="Docker Containerization",
        skill="Kubernetes",
        claimed_level="proficient",
        claim_source="skills_section",
        evidence_strength=0.3,
        evidence_level="WEAK",
        evidence_gaps=[EvidenceGapType.TRANSFERABLE_ONLY],
        verification_required=True,
        consistency_note="Transferable skill identified.",
    )

    questions = generate_verification_questions_for_claim(claim, "org_test", "app_test", "Kubernetes")
    assert len(questions) >= 1
    transfer_q = [q for q in questions if q.evidence_gap == "transferable_only"][0]
    assert "related technologies" in transfer_q.question.lower()
    assert transfer_q.verification_category == VerificationCategory.ARCHITECTURE


def test_verification_api_flow(client, auth_headers):
    # Create a job and analyze requirements
    res_job = client.post(
        "/api/jobs",
        json={
            "title": "Verification Engineer",
            "department": "Platform",
            "location": "Remote",
            "employment_type": "full_time",
            "description": "Must-have: Python, Kubernetes, AWS.",
            "experience_requirement": "5+ years",
        },
        headers=auth_headers,
    )
    assert res_job.status_code == 200
    job_id = res_job.json()["id"]
    client.post(f"/api/jobs/{job_id}/analyze", headers=auth_headers)

    # Seed demo candidate application
    res_summary = client.get("/api/jobs", headers=auth_headers)
    assert res_summary.status_code == 200
