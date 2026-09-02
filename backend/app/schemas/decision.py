from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.enums import CandidateStatus, RecruiterDecisionType


class RecruiterDecisionIn(BaseModel):
    decision: RecruiterDecisionType
    final_status: CandidateStatus | None = None  # required if decision == override
    reason: str | None = None  # required if decision == override


class RecruiterDecisionOut(BaseModel):
    id: UUID
    application_id: UUID
    original_status: CandidateStatus
    decision: RecruiterDecisionType
    final_status: CandidateStatus
    reason: str | None
    recruiter_id: str
    created_at: datetime


class AuditLogEntry(BaseModel):
    id: UUID
    action: str
    object_type: str
    object_id: str
    user_id: str
    metadata: dict
    created_at: datetime
