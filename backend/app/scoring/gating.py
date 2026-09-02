"""Deterministic HUMAN REVIEW gate — spec §25. Pure rule evaluation, no
LLM, no scoring math. The system never auto-rejects; this only ever adds a
flag on top of whatever score was computed."""
from __future__ import annotations

from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.enums import (
    ConsistencyStatus,
    IntegrityCategory,
    MatchStatus,
    RequirementImportance,
)
from app.schemas.integrity import IntegrityReport
from app.schemas.requirement import JobRequirement

LOW_ASSESSMENT_CONFIDENCE = 0.40


def evaluate_human_review_gate(
    requirements: list[JobRequirement],
    assessments: dict[str, RequirementAssessment],
    integrity: IntegrityReport,
    consistency: list[ClaimEvidenceConsistency] | None = None,
) -> tuple[bool, list[str]]:
    reasons: list[str] = []

    if integrity.category == IntegrityCategory.HIGH_RISK:
        reasons.append("Document integrity risk is HIGH — resume shows signs of manipulation.")

    must_haves = [r for r in requirements if r.importance == RequirementImportance.MUST_HAVE]

    for req in must_haves:
        a = assessments.get(req.name)
        if a is None or a.status == MatchStatus.NOT_EVIDENCED:
            reasons.append(f"Must-have requirement '{req.name}' has no supporting evidence.")
        elif a.status == MatchStatus.TRANSFERABLE:
            reasons.append(
                f"Must-have requirement '{req.name}' is only covered by transferable "
                "(not direct) evidence."
            )
        elif a.status == MatchStatus.CONFLICTING:
            reasons.append(f"Conflicting evidence found for must-have requirement '{req.name}'.")
        elif a.confidence < LOW_ASSESSMENT_CONFIDENCE:
            reasons.append(f"Low-confidence assessment on must-have requirement '{req.name}'.")

    for a in assessments.values():
        if a.status == MatchStatus.POTENTIAL_GAMING:
            reasons.append(f"Potential gaming detected on requirement '{a.requirement}'.")

    if consistency:
        conflicting = [c for c in consistency if c.status == ConsistencyStatus.CONFLICTING]
        if conflicting:
            names = ", ".join(c.claim.split(" — ")[0] for c in conflicting[:5])
            more = f" and {len(conflicting) - 5} more" if len(conflicting) > 5 else ""
            reasons.append(
                f"{len(conflicting)} claim(s) found only in suspicious/hidden regions "
                f"of the document ({names}{more})."
            )

    return (len(reasons) > 0, reasons)
