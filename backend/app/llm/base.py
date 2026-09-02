"""Interface every LLM adapter (mock or real) implements. Nothing downstream
should ever import GeminiClient or MockLLM directly — always go through
app.llm.client.get_llm_client() and code against this Protocol."""
from __future__ import annotations

from typing import Protocol

from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.evidence import CandidateClaim
from app.schemas.interview import InterviewQuestion
from app.schemas.requirement import JobRequirement, RequirementExtractionResult
from app.schemas.score import CandidateScores


class LLMClient(Protocol):
    mode: str  # "mock" | "real" — surfaced to the frontend, never hidden

    def extract_requirements(
        self, jd_text: str, experience_requirement: str
    ) -> RequirementExtractionResult: ...

    def extract_claims(self, chunks: list[dict]) -> list[CandidateClaim]:
        """Turn parsed resume chunks into claims with evidence + strength.
        Spec §12."""
        ...

    def assess_requirement(
        self, requirement: JobRequirement, claims: list[CandidateClaim]
    ) -> RequirementAssessment:
        """Spec §22/§38. Must independently justify `status` from the
        evidence handed to it — similarity/keyword hits alone are never
        sufficient proof (spec §15)."""
        ...

    def check_claim_consistency(self, claim: CandidateClaim) -> ClaimEvidenceConsistency:
        """Spec §13."""
        ...

    def generate_interview_questions(
        self, assessments: list[RequirementAssessment], max_questions: int = 4
    ) -> list[InterviewQuestion]:
        """Spec §28. Every question must be grounded in a specific
        assessment (a gap or a strength), never generic."""
        ...

    def executive_summary(
        self, scores: CandidateScores, assessments: list[RequirementAssessment]
    ) -> str:
        """A few sentences, descriptive only — never a hiring recommendation
        (spec §2: the system never makes the final call)."""
        ...
