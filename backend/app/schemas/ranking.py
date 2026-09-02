from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import RankingStatus, SelectionStatus


class RankedCandidate(BaseModel):
    """One row in the ranking table — spec update §8/§17. Descriptive
    only: `ranking_status` is a tier label, never a hiring decision."""

    rank: int
    application_id: UUID
    display_label: str
    match_score: float
    evidence_confidence: float
    document_integrity: float
    must_have_coverage: float  # 0-100, derived from the score breakdown
    preferred_coverage: float  # 0-100
    transferability: float  # 0-100
    ranking_status: RankingStatus
    top_strengths: list[str] = []
    major_gaps: list[str] = []
    human_review_required: bool
    selection_status: SelectionStatus | None = None


class RankingSummary(BaseModel):
    candidates_analyzed: int
    top_match_label: str | None = None
    average_match: float | None = None
    highest_evidence_confidence: float | None = None
    candidates_requiring_review: int = 0


class JobRankingResponse(BaseModel):
    """Spec update §17: the primary candidate dashboard. AI ranks; it
    never shortlists — see `ranking_status` docstring."""

    job_id: UUID
    job_title: str
    ranking_version: int
    summary: RankingSummary
    ranking: list[RankedCandidate]


class SelectionIn(BaseModel):
    selection_status: SelectionStatus
    selection_reason: str | None = None


class SelectionOut(BaseModel):
    application_id: UUID
    recruiter_id: str
    selection_status: SelectionStatus
    selection_reason: str | None = None
    selected_at: datetime
