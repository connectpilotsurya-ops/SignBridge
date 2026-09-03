from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field

from app.schemas.enums import (
    EvidenceGapType,
    QuestionStatus,
    VerificationCategory,
    VerificationStatus,
)


class CandidateClaim(BaseModel):
    id: str
    claim: str
    skill: str
    claimed_level: str  # "basic" | "intermediate" | "advanced" | "expert"
    claim_source: str   # "skills_section" | "experience_summary" | "project_claim"
    evidence_strength: float = Field(ge=0.0, le=1.0)
    evidence_level: str  # "VERY_STRONG" | "STRONG" | "MODERATE" | "WEAK" | "INSUFFICIENT" | "NONE"
    evidence_gaps: list[EvidenceGapType] = Field(default_factory=list)
    verification_required: bool = True
    consistency_note: str = ""


class VerificationQuestionIn(BaseModel):
    claim_id: Optional[str] = None
    requirement_id: Optional[str] = None
    question: str
    purpose: str
    evidence_gap: str
    verification_category: VerificationCategory
    expected_evidence: str = ""
    priority: int = 1


class VerificationQuestionOut(BaseModel):
    id: str
    organization_id: str
    application_id: str
    claim_id: Optional[str] = None
    requirement_id: Optional[str] = None
    question: str
    purpose: str
    evidence_gap: str
    verification_category: VerificationCategory
    expected_evidence: str
    priority: int
    status: QuestionStatus
    recruiter_notes: Optional[str] = None
    created_at: str
    updated_at: str


class VerificationRecordIn(BaseModel):
    verification_status: VerificationStatus
    verification_notes: str = ""


class VerificationRecordOut(BaseModel):
    id: str
    organization_id: str
    application_id: str
    claim_id: Optional[str] = None
    question_id: str
    recruiter_id: str
    verification_status: VerificationStatus
    verification_notes: str
    verified_at: str
    created_at: str


class VerificationSummary(BaseModel):
    application_id: str
    claims: list[CandidateClaim] = Field(default_factory=list)
    questions: list[VerificationQuestionOut] = Field(default_factory=list)
    verifications: list[VerificationRecordOut] = Field(default_factory=list)
