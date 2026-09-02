from __future__ import annotations

from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    """Spec §23-24. Produced ONLY by app/scoring/engine.py — pure Python,
    no LLM call in this file, ever. Every component stored separately so
    the frontend can make each one clickable (spec §49)."""

    must_have_points: float
    must_have_max: float = 35.0
    preferred_points: float
    preferred_max: float = 20.0
    evidence_points: float
    evidence_max: float = 15.0
    experience_points: float
    experience_max: float = 10.0
    transferability_points: float
    transferability_max: float = 10.0
    adaptability_points: float
    adaptability_max: float = 5.0
    integrity_points: float
    integrity_max: float = 5.0

    @property
    def overall(self) -> float:
        return round(
            self.must_have_points
            + self.preferred_points
            + self.evidence_points
            + self.experience_points
            + self.transferability_points
            + self.adaptability_points
            + self.integrity_points,
            1,
        )


class CandidateScores(BaseModel):
    """The three independent top-line numbers — spec §20/§48. Never
    collapsed into one black-box figure."""

    match_score: float = Field(ge=0, le=100)
    evidence_confidence: float = Field(ge=0, le=100)
    document_integrity: float = Field(ge=0, le=100)
    breakdown: ScoreBreakdown
    low_confidence: bool = False
