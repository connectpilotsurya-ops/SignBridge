from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import RequirementCategory, RequirementImportance


class JobRequirement(BaseModel):
    """Matches spec §8 exactly. Extracted by the LLM, never invented beyond
    what's textually present in the JD — the extraction prompt (see
    app/llm/prompts.py) explicitly forbids inferring requirements that
    aren't stated."""

    id: UUID | None = None
    name: str
    category: RequirementCategory
    importance: RequirementImportance
    description: str = ""
    normalized_terms: list[str] = Field(default_factory=list)
    evidence_required: bool = True
    weight: float = 1.0


class RequirementExtractionResult(BaseModel):
    """Top-level LLM structured-output envelope for JD analysis."""

    requirements: list[JobRequirement]
    experience_years_min: float | None = None
    experience_years_max: float | None = None
    notes: str = ""
