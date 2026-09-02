"""Unit tests for the deterministic ranking engine — spec update "ranking,
not shortlisting". Pure functions, no I/O: same inputs must always produce
the same order (no randomness, no LLM)."""
from __future__ import annotations

from app.schemas.enums import RankingStatus
from app.scoring.ranking import RankInput, compute_ranking_status, rank_candidates


def test_sorts_by_match_score_descending():
    rows = [
        RankInput("a", 40, 80, 90, False),
        RankInput("b", 92, 90, 100, False),
        RankInput("c", 70, 80, 90, False),
    ]
    ranked = rank_candidates(rows)
    assert [r.application_id for r in ranked] == ["b", "c", "a"]
    assert [r.rank for r in ranked] == [1, 2, 3]


def test_ties_broken_by_evidence_confidence_then_document_integrity():
    rows = [
        RankInput("low_integrity", 80, 85, 60, False),
        RankInput("high_integrity", 80, 85, 95, False),
        RankInput("low_evidence", 80, 70, 100, False),
    ]
    ranked = rank_candidates(rows)
    # All tied on match_score=80 -> evidence_confidence breaks the first
    # tie (low_evidence loses to both), then document_integrity breaks the
    # remaining tie between the two evidence=85 rows.
    assert [r.application_id for r in ranked] == ["high_integrity", "low_integrity", "low_evidence"]


def test_ranking_is_never_arbitrary_or_random_across_repeated_runs():
    rows = [RankInput(f"c{i}", float(50 + i), 80, 90, False) for i in range(10)]
    first = [r.application_id for r in rank_candidates(rows)]
    for _ in range(5):
        assert [r.application_id for r in rank_candidates(rows)] == first


def test_ranking_status_thresholds_match_spec_worked_examples():
    # Reverse-engineered from the spec update's own worked examples
    # (§8 ranking table / §17 dashboard): 92/90 -> TOP, 88/86/83 -> STRONG,
    # 79 -> POTENTIAL, 41 -> LOWER.
    assert compute_ranking_status(92, False) == RankingStatus.TOP_MATCH
    assert compute_ranking_status(90, False) == RankingStatus.TOP_MATCH
    assert compute_ranking_status(88, False) == RankingStatus.STRONG_MATCH
    assert compute_ranking_status(83, False) == RankingStatus.STRONG_MATCH
    assert compute_ranking_status(79, False) == RankingStatus.POTENTIAL_MATCH
    assert compute_ranking_status(60, False) == RankingStatus.POTENTIAL_MATCH
    assert compute_ranking_status(41, False) == RankingStatus.LOWER_MATCH
    assert compute_ranking_status(0, False) == RankingStatus.LOWER_MATCH


def test_human_review_required_overrides_score_band():
    # A 95 score doesn't quietly become TOP_MATCH if the document still
    # needs a person's attention — human review always wins (spec §15/§17).
    assert compute_ranking_status(95, True) == RankingStatus.HUMAN_REVIEW_REQUIRED
    assert compute_ranking_status(10, True) == RankingStatus.HUMAN_REVIEW_REQUIRED


def test_empty_input_produces_empty_ranking():
    assert rank_candidates([]) == []
