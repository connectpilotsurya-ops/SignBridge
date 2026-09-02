"""Assembles the ranking dashboard response — spec update "ranking, not
shortlisting". This is the one place that turns each candidate's already
-computed, already-deterministic score (from app/scoring/engine.py, via
analysis_runs) into an ordered, explained ranking. It calls the ranking
engine (app/scoring/ranking.py) — never an LLM, never randomness — persists
an immutable snapshot of the result, and merges in the recruiter's own
"selected for next stage" pick, which is a wholly separate stored concept
that this function never mutates the AI's rank or score to reflect.
"""
from __future__ import annotations

import json

from app.persistence.client import get_store
from app.schemas.enums import SelectionStatus
from app.schemas.ranking import JobRankingResponse, RankedCandidate, RankingSummary
from app.schemas.score import ScoreBreakdown
from app.scoring.ranking import RankInput, rank_candidates
from app.services.analysis_view import load_candidate_analysis


def _coverage_pct(points: float, max_points: float) -> float:
    if not max_points:
        return 0.0
    return round(max(0.0, min(1.0, points / max_points)) * 100, 1)


def build_job_ranking(org_id: str, job_id: str) -> JobRankingResponse | None:
    store = get_store()
    job = store.get_job(org_id, job_id)
    if job is None:
        return None

    applications = store.list_applications_for_job(org_id, job_id)
    selections = store.list_selections_for_job(org_id, job_id)

    inputs: list[RankInput] = []
    per_app_extra: dict[str, dict] = {}

    for application in applications:
        run = store.get_latest_analysis(org_id, application["id"])
        if run is None:
            # No analysis yet for this candidate — nothing to rank. They
            # simply don't appear in the ranked list until analysis runs;
            # this is not a rejection, just "not yet evidenced".
            continue

        analysis = load_candidate_analysis(org_id, application["id"], blind_mode=False)
        if analysis is None:
            continue

        breakdown: ScoreBreakdown = analysis.scores.breakdown
        must_have_coverage = _coverage_pct(breakdown.must_have_points, breakdown.must_have_max)
        preferred_coverage = _coverage_pct(breakdown.preferred_points, breakdown.preferred_max)
        transferability = _coverage_pct(breakdown.transferability_points, breakdown.transferability_max)

        strengths = [
            a.requirement
            for a in analysis.requirement_analysis
            if a.status.value in ("exact_match", "equivalent_match", "partial_match")
        ][:3]
        gaps = [
            a.requirement
            for a in analysis.requirement_analysis
            if a.status.value in ("not_evidenced", "potential_gaming")
        ][:3]

        inputs.append(
            RankInput(
                application_id=application["id"],
                match_score=analysis.scores.match_score,
                evidence_confidence=analysis.scores.evidence_confidence,
                document_integrity=analysis.scores.document_integrity,
                human_review_required=analysis.human_review_required,
            )
        )
        per_app_extra[application["id"]] = {
            "display_label": analysis.display_label,
            "must_have_coverage": must_have_coverage,
            "preferred_coverage": preferred_coverage,
            "transferability": transferability,
            "top_strengths": strengths,
            "major_gaps": gaps,
            "human_review_required": analysis.human_review_required,
            "run_id": run["id"],
        }

    ranked = rank_candidates(inputs)

    ranking_version = store.get_ranking_version(org_id, job_id)
    if ranked:
        store.save_ranking_snapshot(
            org_id,
            job_id,
            ranking_version,
            [
                {
                    "application_id": r.application_id,
                    "analysis_run_id": per_app_extra[r.application_id]["run_id"],
                    "rank": r.rank,
                    "match_score": r.match_score,
                    "evidence_confidence": r.evidence_confidence,
                    "document_integrity": r.document_integrity,
                    "ranking_status": r.ranking_status.value,
                }
                for r in ranked
            ],
        )

    rows: list[RankedCandidate] = []
    for r in ranked:
        extra = per_app_extra[r.application_id]
        selection_row = selections.get(r.application_id)
        rows.append(
            RankedCandidate(
                rank=r.rank,
                application_id=r.application_id,
                display_label=extra["display_label"],
                match_score=r.match_score,
                evidence_confidence=r.evidence_confidence,
                document_integrity=r.document_integrity,
                must_have_coverage=extra["must_have_coverage"],
                preferred_coverage=extra["preferred_coverage"],
                transferability=extra["transferability"],
                ranking_status=r.ranking_status,
                top_strengths=extra["top_strengths"],
                major_gaps=extra["major_gaps"],
                human_review_required=extra["human_review_required"],
                selection_status=SelectionStatus(selection_row["selection_status"]) if selection_row else None,
            )
        )

    candidates_analyzed = len(rows)
    summary = RankingSummary(
        candidates_analyzed=candidates_analyzed,
        top_match_label=rows[0].display_label if rows else None,
        average_match=round(sum(r.match_score for r in rows) / candidates_analyzed, 1) if candidates_analyzed else None,
        highest_evidence_confidence=max((r.evidence_confidence for r in rows), default=None),
        candidates_requiring_review=sum(1 for r in rows if r.human_review_required),
    )

    return JobRankingResponse(
        job_id=job["id"],
        job_title=job["title"],
        ranking_version=ranking_version,
        summary=summary,
        ranking=rows,
    )
