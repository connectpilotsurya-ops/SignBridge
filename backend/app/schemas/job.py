from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.schemas.requirement import JobRequirement


class JobCreate(BaseModel):
    title: str
    department: str = ""
    location: str = ""
    employment_type: str = "full_time"
    description: str
    experience_requirement: str = ""


class JobOut(BaseModel):
    id: UUID
    org_id: UUID
    title: str
    department: str
    location: str
    employment_type: str
    description: str
    experience_requirement: str
    requirements: list[JobRequirement] = []
    requirements_analyzed: bool = False
    experience_years_min: float | None = None
    created_at: datetime


class JobSummary(BaseModel):
    """Row shape for the /jobs list and dashboard job cards — spec §32."""

    id: UUID
    title: str
    candidate_count: int
    last_analysis_at: datetime | None
    top_candidate_score: float | None
    review_required_count: int
