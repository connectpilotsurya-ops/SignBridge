from __future__ import annotations

from pydantic import BaseModel


class InterviewQuestion(BaseModel):
    """Spec §28. Must reference a specific evidence gap or a specific
    claimed strength — the mock generator and the Gemini prompt both
    enforce this by requiring `grounded_in` to be non-empty."""

    requirement: str
    question: str
    grounded_in: str  # what evidence (or gap) this question targets
    question_type: str  # "verification" | "depth_probe"
