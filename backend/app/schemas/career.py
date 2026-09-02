from __future__ import annotations

from pydantic import BaseModel, Field


class TrajectoryPoint(BaseModel):
    """One observable step in the candidate's history — spec §18. Strictly
    descriptive of resume content; no future prediction is ever attached
    to this model."""

    period_label: str  # e.g. "2023" or "2023-2024", taken from resume text
    role: str = ""
    technologies: list[str] = Field(default_factory=list)
    responsibility_note: str = ""


class CareerTrajectory(BaseModel):
    points: list[TrajectoryPoint] = Field(default_factory=list)
    summary: str = ""  # descriptive only, never predictive


class AdaptabilityIndicator(BaseModel):
    """Spec §19. Deliberately NOT a personality trait — an evidence-based
    label computed from observable signal counts, not from an LLM opinion."""

    level: str  # "low" | "moderate" | "high"
    technology_transitions: int
    role_transitions: int
    explanation: str  # must read like: "Resume evidence indicates ..."
