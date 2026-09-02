from __future__ import annotations

from pydantic import BaseModel, Field, field_validator

from app.schemas.enums import (
    ConsistencyStatus,
    MatchStatus,
    RelationshipType,
)
from app.schemas.evidence import EvidenceItem


class RequirementAssessment(BaseModel):
    """The LLM's structured interpretation of ONE requirement against the
    retrieved evidence — matches spec §22/§38 exactly.

    This is validated by app/llm/client.py before it ever reaches the
    scoring engine. embedding similarity alone is never treated as proof
    (§15) — the LLM must independently justify `status` from `evidence`.
    """

    requirement: str
    status: MatchStatus
    evidence: list[EvidenceItem] = Field(default_factory=list)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    skill_depth: float = Field(ge=0.0, le=1.0, default=0.0)
    transferability: float | None = Field(default=None, ge=0.0, le=1.0)
    relationship: RelationshipType | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    uncertainty: str = "low"  # low | medium | high
    verification_needed: bool = False
    verification_question: str | None = None
    explanation: str = ""
    why_not: str | None = None

    @field_validator("explanation")
    @classmethod
    def _no_dishonesty_claims(cls, v: str) -> str:
        # Belt-and-suspenders guard against the exact banned phrasings in
        # spec §2 slipping through if a model ever ignores the system
        # prompt. This does not replace the prompt — it's a last-resort net.
        banned = ["is lying", "is dishonest", "fast learner", "personality"]
        low = v.lower()
        for phrase in banned:
            if phrase in low:
                raise ValueError(
                    f"LLM explanation contains banned phrasing: {phrase!r}"
                )
        return v


class ClaimEvidenceConsistency(BaseModel):
    """Spec §13. Never accuses — always frames as a verification need."""

    claim: str
    status: ConsistencyStatus
    explanation: str
