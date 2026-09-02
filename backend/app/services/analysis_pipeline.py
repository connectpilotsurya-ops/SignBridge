"""
The orchestration service — this is the "Detailed pipeline" from spec §5
wired together end to end:

  resume bytes -> PyMuPDF -> integrity -> claims -> [retrieval] ->
  per-requirement assessment -> claim consistency -> career trajectory ->
  adaptability -> deterministic scoring -> human-review gate ->
  capability graph -> interview questions -> executive summary

Every step is a call into a module that has its own single responsibility
(parsing, integrity, scoring, LLM) — this file only sequences them and
never contains scoring math or integrity rules itself.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.embeddings.base import VectorPoint
from app.embeddings.client import get_embedding_client, get_vector_store
from app.graph.builder import build_capability_graph
from app.integrity.detector import analyze_integrity
from app.llm.base import LLMClient
from app.parsing.pdf_parser import UnreadablePDFError, parse_resume_pdf
from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.career import AdaptabilityIndicator, CareerTrajectory
from app.schemas.enums import CandidateStatus, EvidenceStrength
from app.schemas.evidence import CandidateClaim
from app.schemas.graph import CapabilityGraph
from app.schemas.integrity import IntegrityReport
from app.schemas.requirement import JobRequirement
from app.services.career_analysis import parse_year_span
from app.schemas.score import CandidateScores, ScoreBreakdown
from app.scoring.engine import compute_scores
from app.scoring.gating import evaluate_human_review_gate
from app.scoring.weights import POTENTIAL_MATCH_THRESHOLD, STRONG_MATCH_THRESHOLD
from app.services.career_analysis import build_adaptability_indicator, build_career_trajectory

# Claims worth an explicit claim-evidence consistency check — solidly
# SUPPORTED claims (production/achievement/work/project) don't need one;
# this both saves real-mode LLM calls (spec §42) and keeps the consistency
# panel focused on what actually needs recruiter attention.
_CONSISTENCY_CHECK_STRENGTHS = {
    EvidenceStrength.SKILL_LIST_ONLY,
    EvidenceStrength.CONTEXTUAL_MENTION,
    EvidenceStrength.CERTIFICATION,
    EvidenceStrength.SUSPICIOUS,
}

RETRIEVAL_TOP_K = 6


@dataclass
class AnalysisResult:
    scores: CandidateScores
    status: CandidateStatus
    requirement_analysis: list[RequirementAssessment]
    claim_consistency: list[ClaimEvidenceConsistency]
    career_trajectory: CareerTrajectory
    adaptability: AdaptabilityIndicator
    capability_graph: CapabilityGraph
    integrity: IntegrityReport
    interview_questions: list
    executive_summary: str
    human_review_required: bool
    human_review_reasons: list[str]
    analysis_mode: str
    page_count: int = 0
    analysis_incomplete: bool = False
    incomplete_reason: str | None = None


def _empty_incomplete_result(mode: str, reason: str) -> AnalysisResult:
    empty_integrity = IntegrityReport(category="normal", score=0, flags=[], suppressed_terms=[])
    empty_adaptability = AdaptabilityIndicator(level="low", technology_transitions=0, role_transitions=0, explanation="Not computed — analysis incomplete.")
    return AnalysisResult(
        scores=CandidateScores(
            match_score=0, evidence_confidence=0, document_integrity=0,
            breakdown=ScoreBreakdown(
                must_have_points=0, preferred_points=0, evidence_points=0, experience_points=0,
                transferability_points=0, adaptability_points=0, integrity_points=0,
            ),
            low_confidence=True,
        ),
        status=CandidateStatus.REVIEW_REQUIRED,
        requirement_analysis=[],
        claim_consistency=[],
        career_trajectory=CareerTrajectory(points=[], summary="Not computed — analysis incomplete."),
        adaptability=empty_adaptability,
        capability_graph=CapabilityGraph(nodes=[], edges=[]),
        integrity=empty_integrity,
        interview_questions=[],
        executive_summary="Analysis could not be completed for this resume.",
        human_review_required=True,
        human_review_reasons=[reason],
        analysis_mode=mode,
        analysis_incomplete=True,
        incomplete_reason=reason,
    )


def _retrieve_relevant_claims(
    requirement: JobRequirement, claims: list[CandidateClaim], top_k: int = RETRIEVAL_TOP_K
) -> list[CandidateClaim]:
    """Spec §15/§42: narrow the evidence sent to the (real) LLM per
    requirement instead of sending the whole resume every time. Mock mode
    doesn't need this — its matching is exact/graph-based over the full
    claim set, which is cheap and local — so this is only actually applied
    to real-mode Gemini calls (see run_analysis below)."""
    if len(claims) <= top_k:
        return claims
    embedder = get_embedding_client()
    store = get_vector_store()
    collection = "retrieval_scratch"
    store.clear(collection)
    vectors = embedder.embed_texts([c.claim_text for c in claims])
    store.upsert(
        collection,
        [VectorPoint(id=str(i), vector=v, payload={"i": i}) for i, v in enumerate(vectors)],
    )
    q = embedder.embed_texts([f"{requirement.name} {requirement.description}"])[0]
    hits = store.search(collection, q, top_k=top_k)
    return [claims[h[2]["i"]] for h in hits]


def run_analysis(
    llm: LLMClient,
    job_title: str,
    requirements: list[JobRequirement],
    experience_years_min: float | None,
    resume_bytes: bytes,
    candidate_label: str,
) -> AnalysisResult:
    try:
        parsed = parse_resume_pdf(resume_bytes)
    except UnreadablePDFError as exc:
        return _empty_incomplete_result(llm.mode, str(exc))

    integrity = analyze_integrity(parsed.chunks)
    claims = llm.extract_claims(parsed.chunks)

    assessments: list[RequirementAssessment] = []
    for req in requirements:
        candidate_claims = (
            _retrieve_relevant_claims(req, claims) if llm.mode == "real" else claims
        )
        assessments.append(llm.assess_requirement(req, candidate_claims))
    assessments_by_name = {a.requirement: a for a in assessments}

    consistency = [
        llm.check_claim_consistency(c) for c in claims if c.strength in _CONSISTENCY_CHECK_STRENGTHS
    ]

    trajectory = build_career_trajectory(parsed.chunks)
    adaptability = build_adaptability_indicator(trajectory)

    if experience_years_min:
        # Crude but explainable: the earliest start year through the
        # latest end year across every dated period found in the resume,
        # against the JD's stated minimum. Uses parse_year_span so a
        # single ongoing role ("2021 - Present") counts its real tenure
        # instead of collapsing to "one period = one year" — that
        # previously undercounted anyone whose resume only lists one
        # current job.
        spans = [parse_year_span(p.period_label) for p in trajectory.points]
        starts = [s for s, e in spans if s]
        ends = [e for s, e in spans if e]
        years_seen = (max(ends) - min(starts) + 1) if starts and ends else len(trajectory.points)
        experience_fraction = max(0.0, min(1.0, years_seen / experience_years_min))
    else:
        experience_fraction = 0.7  # no stated requirement -> neutral credit, not a penalty

    scores = compute_scores(requirements, assessments_by_name, integrity, adaptability, experience_fraction)

    human_review_required, human_review_reasons = evaluate_human_review_gate(
        requirements, assessments_by_name, integrity, consistency
    )

    if human_review_required:
        status = CandidateStatus.REVIEW_REQUIRED
    elif scores.match_score >= STRONG_MATCH_THRESHOLD:
        status = CandidateStatus.STRONG_MATCH
    elif scores.match_score >= POTENTIAL_MATCH_THRESHOLD:
        status = CandidateStatus.POTENTIAL_MATCH
    else:
        status = CandidateStatus.LOW_MATCH

    capability_graph = build_capability_graph(candidate_label, job_title, requirements, assessments_by_name, claims)
    interview_questions = llm.generate_interview_questions(assessments, max_questions=4)
    executive_summary = llm.executive_summary(scores, assessments)

    return AnalysisResult(
        scores=scores,
        status=status,
        requirement_analysis=assessments,
        claim_consistency=consistency,
        career_trajectory=trajectory,
        adaptability=adaptability,
        capability_graph=capability_graph,
        integrity=integrity,
        interview_questions=interview_questions,
        executive_summary=executive_summary,
        human_review_required=human_review_required,
        human_review_reasons=human_review_reasons,
        analysis_mode=llm.mode,
        page_count=parsed.page_count,
    )
