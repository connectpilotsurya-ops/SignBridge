"""
Deterministic ranking engine — spec update "ranking, not shortlisting".

Takes every candidate's already-computed scores (from
app/scoring/engine.py — itself zero-LLM) and produces an ordered rank
plus a descriptive ranking_status. No LLM involvement anywhere in this
file, no randomness: the same set of scores always produces the same
order. The AI's job stops at "here is the evidence-backed match score for
every candidate" — this module only sorts and labels, it never decides
who advances.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas.enums import RankingStatus

# Score bands for the descriptive ranking_status. Human review always
# takes priority over the band — a candidate is never quietly labeled by
# score while something about their document still needs a person's
# attention (spec update §15/§17).
TOP_MATCH_THRESHOLD = 90.0
STRONG_MATCH_THRESHOLD = 80.0
POTENTIAL_MATCH_THRESHOLD = 60.0


@dataclass
class RankInput:
    application_id: str
    match_score: float
    evidence_confidence: float
    document_integrity: float
    human_review_required: bool


@dataclass
class RankOutput:
    application_id: str
    rank: int
    match_score: float
    evidence_confidence: float
    document_integrity: float
    ranking_status: RankingStatus


def compute_ranking_status(match_score: float, human_review_required: bool) -> RankingStatus:
    """A descriptive ranking tier — never a hiring decision. 'Lower match'
    means the currently available evidence supports a weaker match, not
    that the candidate should be rejected (spec update §14)."""
    if human_review_required:
        return RankingStatus.HUMAN_REVIEW_REQUIRED
    if match_score >= TOP_MATCH_THRESHOLD:
        return RankingStatus.TOP_MATCH
    if match_score >= STRONG_MATCH_THRESHOLD:
        return RankingStatus.STRONG_MATCH
    if match_score >= POTENTIAL_MATCH_THRESHOLD:
        return RankingStatus.POTENTIAL_MATCH
    return RankingStatus.LOWER_MATCH


def rank_candidates(rows: list[RankInput]) -> list[RankOutput]:
    """Sort by match_score desc, then evidence_confidence desc, then
    document_integrity desc as tie-breakers (spec update §5) — never an
    arbitrary or random order. Python's sort is stable, so candidates
    tied on all three keep their original relative order rather than
    reshuffling between identical runs."""
    ordered = sorted(
        rows,
        key=lambda r: (-r.match_score, -r.evidence_confidence, -r.document_integrity),
    )
    return [
        RankOutput(
            application_id=r.application_id,
            rank=i + 1,
            match_score=r.match_score,
            evidence_confidence=r.evidence_confidence,
            document_integrity=r.document_integrity,
            ranking_status=compute_ranking_status(r.match_score, r.human_review_required),
        )
        for i, r in enumerate(ordered)
    ]
