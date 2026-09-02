from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.career import AdaptabilityIndicator, CareerTrajectory
from app.schemas.enums import CandidateStatus, ResumeStatus
from app.schemas.graph import CapabilityGraph
from app.schemas.integrity import IntegrityReport
from app.schemas.interview import InterviewQuestion
from app.schemas.score import CandidateScores


class CandidateRow(BaseModel):
    """One row in the candidate table — spec §32."""

    application_id: UUID
    display_label: str  # "Candidate #014" in blind mode, real name otherwise
    match_score: float
    evidence_confidence: float
    document_integrity: float
    status: CandidateStatus
    top_strengths: list[str] = []
    major_gaps: list[str] = []
    resume_status: ResumeStatus


class CandidateAnalysis(BaseModel):
    """Full payload for /candidates/[id] — spec §33. Every section listed
    there is a field on this model so the frontend can render top-to-bottom
    off one response."""

    application_id: UUID
    display_label: str
    blind_mode: bool
    scores: CandidateScores
    status: CandidateStatus
    executive_summary: str
    requirement_analysis: list[RequirementAssessment]
    claim_consistency: list[ClaimEvidenceConsistency]
    career_trajectory: CareerTrajectory
    adaptability: AdaptabilityIndicator
    capability_graph: CapabilityGraph
    integrity: IntegrityReport
    interview_questions: list[InterviewQuestion]
    human_review_required: bool = False
    human_review_reasons: list[str] = []
    analysis_mode: str  # "mock" | "real" — never hidden from the recruiter
    analysis_incomplete: bool = False
    incomplete_reason: str | None = None
    created_at: datetime
