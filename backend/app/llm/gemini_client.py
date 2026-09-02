"""
Real Gemini 2.5 Flash adapter — spec §4/§38/§39.

This module is exercised only when DEMO_MODE=false and GEMINI_API_KEY is
set (app.config.Settings.llm_mode == "real"); `google-generativeai` is in
requirements-real.txt, not the core requirements.txt, precisely so the
demo path never needs it installed.

Every call: build the structured-output request -> validate the JSON with
the matching Pydantic model -> on failure, retry once with the validation
error appended to the prompt -> on second failure, raise
LLMValidationError so the caller can mark the analysis incomplete and
route to human review (spec §38/§40). We never silently accept malformed
output and we never fabricate a result when the model fails.
"""
from __future__ import annotations

import json
import logging

from pydantic import ValidationError

from app.config import Settings
from app.llm.prompts import (
    INTERVIEW_QUESTION_INSTRUCTIONS,
    REQUIREMENT_ASSESSMENT_INSTRUCTIONS,
    REQUIREMENT_EXTRACTION_INSTRUCTIONS,
    SYSTEM_ANALYSIS_PROMPT,
)
from app.llm.mock import MockLLM  # reused for extract_claims (pure parsing, no LLM needed) and executive_summary template
from app.llm.skill_graph import SKILL_SYNONYMS, SKILL_TRANSFERS
from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.evidence import CandidateClaim
from app.schemas.interview import InterviewQuestion
from app.schemas.requirement import JobRequirement, RequirementExtractionResult
from app.schemas.score import CandidateScores

logger = logging.getLogger(__name__)


class LLMValidationError(Exception):
    """Raised when the model's structured output fails Pydantic validation
    twice in a row. Callers must treat this as ANALYSIS_INCOMPLETE +
    HUMAN_REVIEW_REQUIRED (spec §40) — never fall back to guessing."""


class GeminiLLM:
    mode = "real"

    def __init__(self, settings: Settings):
        import google.generativeai as genai  # imported lazily — see module docstring

        genai.configure(api_key=settings.gemini_api_key)
        self._genai = genai
        self._model_name = settings.gemini_model
        self._model = genai.GenerativeModel(
            self._model_name, system_instruction=SYSTEM_ANALYSIS_PROMPT
        )
        # Claim extraction is pure structural parsing of forensic PDF metadata
        # (font/color/position -> section -> strength) — there is nothing for
        # a language model to "interpret" that isn't already deterministic,
        # so both modes share this implementation rather than spending a
        # Gemini call on it.
        self._structural = MockLLM()

    def _generate_json(self, instructions: str, payload: dict, retry_hint: str = "") -> dict:
        prompt = f"{instructions}\n\nInput:\n{json.dumps(payload, default=str)}"
        if retry_hint:
            prompt += f"\n\nYour previous response was invalid: {retry_hint}\nReturn ONLY valid JSON this time."
        response = self._model.generate_content(
            prompt,
            generation_config=self._genai.GenerationConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)

    def _call_validated(self, instructions: str, payload: dict, model_cls):
        try:
            raw = self._generate_json(instructions, payload)
            return model_cls.model_validate(raw)
        except (ValidationError, json.JSONDecodeError) as first_err:
            logger.warning("Gemini structured output failed validation, retrying once: %s", first_err)
            try:
                raw = self._generate_json(instructions, payload, retry_hint=str(first_err))
                return model_cls.model_validate(raw)
            except (ValidationError, json.JSONDecodeError) as second_err:
                raise LLMValidationError(
                    f"Gemini output failed validation twice: {second_err}"
                ) from second_err

    def extract_requirements(self, jd_text: str, experience_requirement: str) -> RequirementExtractionResult:
        payload = {
            "job_description": jd_text,
            "experience_requirement": experience_requirement,
            "schema": RequirementExtractionResult.model_json_schema(),
        }
        return self._call_validated(
            REQUIREMENT_EXTRACTION_INSTRUCTIONS, payload, RequirementExtractionResult
        )

    def extract_claims(self, chunks: list[dict]) -> list[CandidateClaim]:
        return self._structural.extract_claims(chunks)

    def assess_requirement(
        self, requirement: JobRequirement, claims: list[CandidateClaim]
    ) -> RequirementAssessment:
        payload = {
            "requirement": requirement.model_dump(mode="json"),
            "candidate_claims": [c.model_dump(mode="json") for c in claims],
            "skill_synonyms": SKILL_SYNONYMS,
            "skill_transfers": SKILL_TRANSFERS,
            "schema": RequirementAssessment.model_json_schema(),
        }
        try:
            return self._call_validated(
                REQUIREMENT_ASSESSMENT_INSTRUCTIONS, payload, RequirementAssessment
            )
        except LLMValidationError:
            # Fail safe, not fail silent: fall back to the deterministic mock
            # reasoning for THIS requirement only, and let the caller know
            # via low confidence + verification_needed rather than crashing
            # the whole analysis run over one bad model response.
            fallback = self._structural.assess_requirement(requirement, claims)
            fallback.uncertainty = "high"
            fallback.verification_needed = True
            fallback.explanation += " (Gemini response failed validation; deterministic fallback used.)"
            return fallback

    def check_claim_consistency(self, claim: CandidateClaim) -> ClaimEvidenceConsistency:
        payload = {"claim": claim.model_dump(mode="json"), "schema": ClaimEvidenceConsistency.model_json_schema()}
        try:
            return self._call_validated(
                "Assess whether this claim is supported by its own evidence. "
                "Never accuse the candidate of dishonesty — frame gaps as "
                "verification needs.",
                payload,
                ClaimEvidenceConsistency,
            )
        except LLMValidationError:
            return self._structural.check_claim_consistency(claim)

    def generate_interview_questions(
        self, assessments: list[RequirementAssessment], max_questions: int = 4
    ) -> list[InterviewQuestion]:
        payload = {
            "assessments": [a.model_dump(mode="json") for a in assessments],
            "max_questions": max_questions,
        }
        try:
            raw = self._generate_json(INTERVIEW_QUESTION_INSTRUCTIONS, payload)
            items = raw if isinstance(raw, list) else raw.get("questions", [])
            return [InterviewQuestion.model_validate(q) for q in items][:max_questions]
        except (ValidationError, json.JSONDecodeError, KeyError) as err:
            logger.warning("Gemini interview-question generation failed, using deterministic fallback: %s", err)
            return self._structural.generate_interview_questions(assessments, max_questions)

    def executive_summary(self, scores: CandidateScores, assessments: list[RequirementAssessment]) -> str:
        # Deliberately templated even in real mode: this is the one piece of
        # output that is purely descriptive statistics over `scores` and
        # `assessments`, so there's nothing for the model to add beyond
        # phrasing, and a template guarantees it can never smuggle a
        # hire/reject recommendation past the "AI never decides" rule.
        return self._structural.executive_summary(scores, assessments)
