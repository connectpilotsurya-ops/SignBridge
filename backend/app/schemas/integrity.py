from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.enums import IntegrityCategory, IntegrityFlagType, IntegritySeverity


class IntegrityFlag(BaseModel):
    """Spec §11 exactly. Produced by app/integrity/detector.py — pure
    deterministic logic over PyMuPDF metadata, no LLM involved. We mark
    suspicious content, we never delete it."""

    type: IntegrityFlagType
    severity: IntegritySeverity
    description: str
    page: int
    evidence_text: str
    confidence: float = Field(ge=0.0, le=1.0)


class IntegrityReport(BaseModel):
    category: IntegrityCategory
    score: int = Field(ge=0, le=100)  # DOCUMENT INTEGRITY score
    flags: list[IntegrityFlag] = Field(default_factory=list)
    suppressed_terms: list[str] = Field(
        default_factory=list,
        description="Terms whose matching_weight was zeroed/reduced because "
        "they were only found in a suspicious region.",
    )
