from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.enums import EvidenceSource, EvidenceStrength


class EvidenceItem(BaseModel):
    """One piece of textual proof, always traceable back to a resume page.

    `text` must be a substring that actually appears in the resume — the
    LLM is instructed never to paraphrase evidence into something that
    reads better (see app/llm/prompts.py SYSTEM_ANALYSIS_PROMPT).
    """

    text: str
    source: EvidenceSource
    page: int | None = None
    chunk_id: UUID | None = None


class CandidateClaim(BaseModel):
    """A claim extracted from the resume, distinct from whether it's backed
    up. Spec §12: 'Kubernetes — Advanced' in a skills list is a claim with
    EvidenceStrength.SKILL_LIST_ONLY, not a verified capability."""

    id: UUID | None = None
    skill_or_topic: str
    claim_text: str
    evidence: list[EvidenceItem] = Field(default_factory=list)
    strength: EvidenceStrength
    section: str = "unknown"
