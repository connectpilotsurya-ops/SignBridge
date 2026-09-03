"""
AI INTERVIEW VERIFICATION ENGINE
"From Resume Claims to Meaningful Interview Questions"

Analyzes candidate claims against verified resume evidence, detects evidence gaps,
computes non-accusatory consistency assessments, and generates 8-category interview questions.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas.enums import (
    EvidenceGapType,
    QuestionStatus,
    VerificationCategory,
)
from app.schemas.verification import (
    CandidateClaim,
    VerificationQuestionOut,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def classify_evidence_level(score: float, has_production: bool, has_hidden: bool) -> str:
    if has_hidden and score < 0.2:
        return "NONE"
    if score >= 0.85 and has_production:
        return "VERY_STRONG"
    if score >= 0.7:
        return "STRONG"
    if score >= 0.5:
        return "MODERATE"
    if score >= 0.25:
        return "WEAK"
    if score > 0:
        return "INSUFFICIENT"
    return "NONE"


def generate_verification_questions_for_claim(
    claim: CandidateClaim,
    org_id: str,
    application_id: str,
    requirement_name: str = "",
) -> list[VerificationQuestionOut]:
    questions: list[VerificationQuestionOut] = []
    skill = claim.skill
    now_str = _now()

    gaps = set(claim.evidence_gaps)

    # 1. OWNERSHIP (Moderate Technical Depth)
    if EvidenceGapType.MISSING_OWNERSHIP_EVIDENCE in gaps:
        questions.append(
            VerificationQuestionOut(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                application_id=application_id,
                claim_id=claim.id,
                requirement_id=None,
                question=f"What core components or infrastructure of the {skill} pipeline did you personally architect vs delegate, and what key design trade-offs did you evaluate?",
                purpose="Verify hands-on ownership, architectural decision-making, and individual contribution.",
                evidence_gap="missing_ownership_evidence",
                verification_category=VerificationCategory.OWNERSHIP,
                expected_evidence="Concrete breakdown of repos, modules, design patterns, and engineering trade-offs owned personally.",
                priority=1,
                status=QuestionStatus.GENERATED,
                created_at=now_str,
                updated_at=now_str,
            )
        )

    # 2. EXPERIENCE / PRODUCTION (Moderate Failure Recovery Probe)
    if EvidenceGapType.MISSING_PRODUCTION_EVIDENCE in gaps:
        questions.append(
            VerificationQuestionOut(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                application_id=application_id,
                claim_id=claim.id,
                requirement_id=None,
                question=f"Describe a non-trivial production incident or outage involving {skill}. What root-cause diagnostic tools did you use, and how did you verify the post-mortem fix?",
                purpose="Verify operational troubleshooting, telemetry analysis, and production resilience.",
                evidence_gap="missing_production_evidence",
                verification_category=VerificationCategory.EXPERIENCE,
                expected_evidence="Diagnostic timeline, telemetry metrics (logs, traces, flame graphs), and root-cause post-mortem details.",
                priority=1,
                status=QuestionStatus.GENERATED,
                created_at=now_str,
                updated_at=now_str,
            )
        )

    # 3. SCALE (Moderate Throughput & Concurrency Bottleneck Probe)
    if EvidenceGapType.MISSING_SCALE_EVIDENCE in gaps:
        questions.append(
            VerificationQuestionOut(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                application_id=application_id,
                claim_id=claim.id,
                requirement_id=None,
                question=f"Walk through the memory, network, or concurrency bottlenecks you encountered when scaling {skill} under heavy concurrent traffic.",
                purpose="Verify system scaling limits, resource optimization, and throughput capacity knowledge.",
                evidence_gap="missing_scale_evidence",
                verification_category=VerificationCategory.SCALE,
                expected_evidence="Quantifiable metrics (QPS, p99 latency, RAM/CPU allocation, cache hit ratios).",
                priority=2,
                status=QuestionStatus.GENERATED,
                created_at=now_str,
                updated_at=now_str,
            )
        )

    # 4. TRANSFERABLE ONLY (Moderate Domain Transition Probe)
    if EvidenceGapType.TRANSFERABLE_ONLY in gaps:
        questions.append(
            VerificationQuestionOut(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                application_id=application_id,
                claim_id=claim.id,
                requirement_id=None,
                question=f"You have experience with related technologies. How would you design a fault-tolerant, scalable {skill} service from scratch, and how would you handle data inconsistency or split-brain scenarios?",
                purpose="Verify architectural adaptability, core system design principles, and edge-case handling.",
                evidence_gap="transferable_only",
                verification_category=VerificationCategory.ARCHITECTURE,
                expected_evidence="Methodical architectural design covering data consistency, partitioning, failover, and monitoring.",
                priority=1,
                status=QuestionStatus.GENERATED,
                created_at=now_str,
                updated_at=now_str,
            )
        )

    # 5. DEPTH / TROUBLESHOOTING (Moderate Complex Architecture Probe)
    if not questions or EvidenceGapType.CLAIMED_EXPERTISE_EXCEEDS_EVIDENCE in gaps:
        questions.append(
            VerificationQuestionOut(
                id=str(uuid.uuid4()),
                organization_id=org_id,
                application_id=application_id,
                claim_id=claim.id,
                requirement_id=None,
                question=f"Explain a complex failure mode in {skill} (such as race conditions, memory leaks, or cascading failures) and how you engineered system resilience against it.",
                purpose="Verify technical depth, concurrency handling, and failure mitigation strategies.",
                evidence_gap="claimed_expertise_exceeds_evidence",
                verification_category=VerificationCategory.DEPTH,
                expected_evidence="Technical explanation of edge-case bugs, locking mechanisms, thread safety, or circuit breaker patterns.",
                priority=2,
                status=QuestionStatus.GENERATED,
                created_at=now_str,
                updated_at=now_str,
            )
        )

    return questions


def analyze_candidate_verifications(
    org_id: str,
    application_id: str,
    requirement_assessments: list,
    integrity_report: dict | None = None,
) -> tuple[list[CandidateClaim], list[VerificationQuestionOut]]:
    claims: list[CandidateClaim] = []
    questions: list[VerificationQuestionOut] = []

    hidden_terms = set(integrity_report.get("suppressed_terms", [])) if integrity_report else set()

    for idx, req in enumerate(requirement_assessments):
        req_name = req.get("requirement") if isinstance(req, dict) else getattr(req, "requirement", "")
        status_val = req.get("status") if isinstance(req, dict) else getattr(req, "status", "not_evidenced")
        evidence_list = req.get("evidence", []) if isinstance(req, dict) else getattr(req, "evidence", [])
        evidence_strength = req.get("evidence_strength", 0.0) if isinstance(req, dict) else getattr(req, "evidence_strength", 0.0)

        # Check evidence gaps
        gaps: list[EvidenceGapType] = []

        is_hidden = any(term.lower() in req_name.lower() for term in hidden_terms)
        if is_hidden:
            gaps.append(EvidenceGapType.HIDDEN_TEXT_ONLY)

        if status_val == "transferable":
            gaps.append(EvidenceGapType.TRANSFERABLE_ONLY)
        elif status_val in ("not_evidenced", "partial_match", "potential_gaming"):
            gaps.append(EvidenceGapType.MISSING_PRODUCTION_EVIDENCE)
            gaps.append(EvidenceGapType.MISSING_OWNERSHIP_EVIDENCE)
            gaps.append(EvidenceGapType.MISSING_SCALE_EVIDENCE)
            gaps.append(EvidenceGapType.MISSING_PROJECT_DETAILS)

        if evidence_strength < 0.6 and status_val != "exact_match":
            gaps.append(EvidenceGapType.CLAIMED_EXPERTISE_EXCEEDS_EVIDENCE)

        evidence_level = classify_evidence_level(evidence_strength, len(evidence_list) > 1, is_hidden)

        # Generate non-accusatory consistency note
        if status_val == "exact_match" and evidence_level in ("VERY_STRONG", "STRONG"):
            consistency_note = f"Evidence strongly supports demonstrated production capability in {req_name}."
        elif status_val == "transferable":
            consistency_note = f"Direct {req_name} evidence is limited, but high transferable skill signal was identified."
        elif is_hidden:
            consistency_note = f"{req_name} was detected only in unverified or suspicious document runs."
        else:
            consistency_note = f"The resume indicates {req_name} capability, but provides limited supporting evidence regarding ownership, production usage, or scale."

        claim_obj = CandidateClaim(
            id=f"claim_{idx}_{uuid.uuid4().hex[:6]}",
            claim=f"Evidenced capability in {req_name}",
            skill=req_name,
            claimed_level="advanced" if evidence_strength > 0.5 else "proficient",
            claim_source="requirement_matching",
            evidence_strength=evidence_strength,
            evidence_level=evidence_level,
            evidence_gaps=gaps,
            verification_required=len(gaps) > 0,
            consistency_note=consistency_note,
        )
        claims.append(claim_obj)

        if claim_obj.verification_required:
            q_list = generate_verification_questions_for_claim(claim_obj, org_id, application_id, req_name)
            questions.extend(q_list)

    return claims, questions
