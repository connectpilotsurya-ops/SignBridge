"""
Deterministic scoring engine — spec §23/§54: "LLM: interpretation. Python:
deterministic scoring." No network call, no randomness, no model weights
anywhere in this file. Same inputs always produce the same score, and the
score is reproducible/auditable by a human reading this file top to bottom.
"""
from __future__ import annotations

from app.schemas.career import AdaptabilityIndicator
from app.schemas.enums import MatchStatus, RequirementImportance
from app.schemas.integrity import IntegrityReport
from app.schemas.requirement import JobRequirement
from app.schemas.score import CandidateScores, ScoreBreakdown
from app.scoring.weights import (
    ADAPTABILITY_LEVEL_FLOAT,
    ADAPTABILITY_MAX,
    EVIDENCE_MAX,
    EXPERIENCE_MAX,
    GAP_FRACTION_THRESHOLD,
    INTEGRITY_MAX,
    LOW_CONFIDENCE_THRESHOLD,
    MUST_HAVE_MAX,
    PREFERRED_MAX,
    STATUS_FRACTION_RANGE,
    TRANSFERABILITY_MAX,
)


def requirement_fraction(status: MatchStatus, evidence_strength: float, transferability: float | None) -> float:
    """The fraction of a single requirement's weight that gets credited,
    given its match status and supporting strength. See weights.py for the
    band each status maps to."""
    low, high = STATUS_FRACTION_RANGE[status]
    if low == high:
        return low
    driver = transferability if status == MatchStatus.TRANSFERABLE else evidence_strength
    driver = max(0.0, min(1.0, driver if driver is not None else 0.0))
    return round(low + (high - low) * driver, 4)


def _weighted_avg(pairs: list[tuple[float, float]]) -> float:
    """pairs = [(value, weight), ...]"""
    total_w = sum(w for _, w in pairs)
    if total_w <= 0:
        return 0.0
    return sum(v * w for v, w in pairs) / total_w


def compute_scores(
    requirements: list[JobRequirement],
    assessments: dict[str, "RequirementAssessment"],  # keyed by requirement name  # noqa: F821
    integrity: IntegrityReport,
    adaptability: AdaptabilityIndicator,
    experience_fraction: float = 0.6,
) -> CandidateScores:
    must_haves = [r for r in requirements if r.importance == RequirementImportance.MUST_HAVE]
    preferreds = [r for r in requirements if r.importance == RequirementImportance.PREFERRED]

    def fraction_for(req: JobRequirement) -> float:
        a = assessments.get(req.name)
        if a is None:
            return 0.0  # no assessment produced -> treated as not evidenced, never silently skipped
        return requirement_fraction(a.status, a.evidence_strength, a.transferability)

    must_pairs = [(fraction_for(r), r.weight) for r in must_haves]
    pref_pairs = [(fraction_for(r), r.weight) for r in preferreds]

    must_have_points = MUST_HAVE_MAX * (_weighted_avg(must_pairs) if must_pairs else 1.0)
    preferred_points = PREFERRED_MAX * (_weighted_avg(pref_pairs) if pref_pairs else 1.0)

    # ---- evidence strength component (all requirements, importance-weighted)
    all_reqs = must_haves + preferreds
    evidence_pairs = [
        (assessments[r.name].evidence_strength, r.weight)
        for r in all_reqs
        if r.name in assessments
    ]
    evidence_points = EVIDENCE_MAX * (_weighted_avg(evidence_pairs) if evidence_pairs else 0.0)

    # ---- experience component --------------------------------------------
    experience_points = EXPERIENCE_MAX * max(0.0, min(1.0, experience_fraction))

    # ---- transferability component -----------------------------------------
    # Only meaningful for requirements that weren't solidly matched on direct
    # evidence ("gaps"). No gaps -> nothing needed transferring -> full marks.
    gaps = [r for r in all_reqs if fraction_for(r) < GAP_FRACTION_THRESHOLD]
    if not gaps:
        transferability_points = TRANSFERABILITY_MAX
    else:
        gap_vals = []
        for r in gaps:
            a = assessments.get(r.name)
            if a and a.status == MatchStatus.TRANSFERABLE and a.transferability is not None:
                gap_vals.append(a.transferability)
            else:
                gap_vals.append(0.0)
        transferability_points = TRANSFERABILITY_MAX * (sum(gap_vals) / len(gap_vals))

    # ---- adaptability component ---------------------------------------------
    adaptability_points = ADAPTABILITY_MAX * ADAPTABILITY_LEVEL_FLOAT.get(adaptability.level, 0.5)

    # ---- integrity component -------------------------------------------------
    integrity_points = INTEGRITY_MAX * (integrity.score / 100.0)

    breakdown = ScoreBreakdown(
        must_have_points=round(must_have_points, 2),
        preferred_points=round(preferred_points, 2),
        evidence_points=round(evidence_points, 2),
        experience_points=round(experience_points, 2),
        transferability_points=round(transferability_points, 2),
        adaptability_points=round(adaptability_points, 2),
        integrity_points=round(integrity_points, 2),
    )

    confidence_pairs = [
        (assessments[r.name].confidence, r.weight) for r in all_reqs if r.name in assessments
    ]
    evidence_confidence = round(100 * (_weighted_avg(confidence_pairs) if confidence_pairs else 0.0), 1)

    return CandidateScores(
        match_score=breakdown.overall,
        evidence_confidence=evidence_confidence,
        document_integrity=float(integrity.score),
        breakdown=breakdown,
        low_confidence=evidence_confidence < LOW_CONFIDENCE_THRESHOLD,
    )
