"""Spec §23-25: the deterministic scoring engine and the human-review
gate. No LLM call happens anywhere in this file — every input is a
hand-built Pydantic object, exactly what the real pipeline hands these
two modules after the LLM step has already run."""
from __future__ import annotations

import pytest

from app.schemas.assessment import RequirementAssessment
from app.schemas.career import AdaptabilityIndicator
from app.schemas.enums import (
    IntegrityCategory,
    MatchStatus,
    RequirementCategory,
    RequirementImportance,
)
from app.schemas.integrity import IntegrityReport
from app.schemas.requirement import JobRequirement
from app.scoring.engine import compute_scores
from app.scoring.gating import evaluate_human_review_gate

NORMAL_INTEGRITY = IntegrityReport(category=IntegrityCategory.NORMAL, score=100)
NEUTRAL_ADAPTABILITY = AdaptabilityIndicator(level="moderate", technology_transitions=0, role_transitions=0, explanation="")


def _req(name: str, importance: RequirementImportance) -> JobRequirement:
    return JobRequirement(name=name, category=RequirementCategory.TECHNICAL_SKILL, importance=importance)


def _assessment(name: str, status: MatchStatus, evidence_strength=1.0, confidence=0.9, transferability=None) -> RequirementAssessment:
    return RequirementAssessment(
        requirement=name, status=status, evidence_strength=evidence_strength,
        confidence=confidence, transferability=transferability,
    )


def test_scoring_is_deterministic():
    """Same inputs must always produce the exact same score — spec §23's
    core promise. No randomness, no model call, anywhere in this path."""
    requirements = [_req("Python", RequirementImportance.MUST_HAVE)]
    assessments = {"Python": _assessment("Python", MatchStatus.EXACT_MATCH)}

    first = compute_scores(requirements, assessments, NORMAL_INTEGRITY, NEUTRAL_ADAPTABILITY)
    second = compute_scores(requirements, assessments, NORMAL_INTEGRITY, NEUTRAL_ADAPTABILITY)
    assert first.model_dump() == second.model_dump()


def test_missing_must_have_lowers_score_and_triggers_review():
    requirements = [
        _req("Python", RequirementImportance.MUST_HAVE),
        _req("AWS", RequirementImportance.MUST_HAVE),
    ]
    assessments = {
        "Python": _assessment("Python", MatchStatus.EXACT_MATCH),
        "AWS": _assessment("AWS", MatchStatus.NOT_EVIDENCED, evidence_strength=0.0, confidence=0.9),
    }
    scores = compute_scores(requirements, assessments, NORMAL_INTEGRITY, NEUTRAL_ADAPTABILITY)
    # One of two must-haves entirely unmet -> well under half of must-have points.
    assert scores.breakdown.must_have_points < scores.breakdown.must_have_max * 0.6

    required, reasons = evaluate_human_review_gate(requirements, assessments, NORMAL_INTEGRITY)
    assert required is True
    assert any("AWS" in r for r in reasons)


def test_full_match_needs_no_review():
    requirements = [_req("Python", RequirementImportance.MUST_HAVE)]
    assessments = {"Python": _assessment("Python", MatchStatus.EXACT_MATCH)}
    required, reasons = evaluate_human_review_gate(requirements, assessments, NORMAL_INTEGRITY)
    assert required is False
    assert reasons == []


def test_high_risk_integrity_always_triggers_review_even_with_full_scores():
    requirements = [_req("Python", RequirementImportance.MUST_HAVE)]
    assessments = {"Python": _assessment("Python", MatchStatus.EXACT_MATCH)}
    high_risk = IntegrityReport(category=IntegrityCategory.HIGH_RISK, score=50)
    required, reasons = evaluate_human_review_gate(requirements, assessments, high_risk)
    assert required is True
    assert any("integrity" in r.lower() for r in reasons)


def test_potential_gaming_status_triggers_review():
    requirements = [_req("Kubernetes", RequirementImportance.PREFERRED)]
    assessments = {"Kubernetes": _assessment("Kubernetes", MatchStatus.POTENTIAL_GAMING, evidence_strength=0.0, confidence=0.9)}
    required, reasons = evaluate_human_review_gate(requirements, assessments, NORMAL_INTEGRITY)
    assert required is True
    assert any("gaming" in r.lower() for r in reasons)


def test_explanation_cannot_contain_banned_dishonesty_phrasing():
    """Spec §2's responsible-AI rule enforced as a Pydantic validator: the
    system must never accuse a candidate of lying, and must never
    fabricate a personality/soft-skill judgement from a resume."""
    with pytest.raises(ValueError, match="banned phrasing"):
        RequirementAssessment(
            requirement="Python", status=MatchStatus.NOT_EVIDENCED,
            evidence_strength=0.0, confidence=0.5,
            explanation="This candidate is lying about their experience.",
        )

    with pytest.raises(ValueError, match="banned phrasing"):
        RequirementAssessment(
            requirement="Python", status=MatchStatus.EXACT_MATCH,
            evidence_strength=1.0, confidence=0.9,
            explanation="Seems like a fast learner based on this resume.",
        )

    # A properly-worded, evidence-only explanation must pass through untouched.
    ok = RequirementAssessment(
        requirement="Python", status=MatchStatus.NOT_EVIDENCED,
        evidence_strength=0.0, confidence=0.5,
        explanation="No direct or transferable evidence of Python found in the resume.",
    )
    assert "No direct" in ok.explanation
