"""
Rule-based mock LLM adapter — the default (DEMO_MODE=true) reasoning
engine. It is deliberately built to obey the exact same rules the real
Gemini adapter is prompted with (see prompts.py): it never claims direct
evidence for something it can't point to a chunk for, it never collapses
transferable into exact, and it never editorializes about honesty.

Every "reasoning" step here is a plain, readable rule over the structured
claims produced by extract_claims() — nothing here calls out to a model,
so it's 100% reproducible and free to run, which is the whole point of
demo mode existing.
"""
from __future__ import annotations

import re

from app.parsing.constants import DISPLAY_NAMES, TECH_VOCAB
from app.schemas.assessment import ClaimEvidenceConsistency, RequirementAssessment
from app.schemas.enums import (
    ConsistencyStatus,
    EvidenceSource,
    EvidenceStrength,
    MatchStatus,
    RelationshipType,
    RequirementCategory,
    RequirementImportance,
)
from app.schemas.evidence import CandidateClaim, EvidenceItem
from app.schemas.interview import InterviewQuestion
from app.schemas.requirement import JobRequirement, RequirementExtractionResult
from app.schemas.score import CandidateScores
from app.scoring.weights import EVIDENCE_STRENGTH_FLOAT
from app.llm.skill_graph import canonical_name, transfer_candidates

_STRENGTH_ORDER = list(EvidenceStrength)  # weakest -> strongest, as declared in enums.py

_SECTION_TO_SOURCE = {
    "experience": EvidenceSource.WORK_EXPERIENCE,
    "projects": EvidenceSource.PROJECT,
    "achievements": EvidenceSource.ACHIEVEMENT,
    "certifications": EvidenceSource.CERTIFICATION,
    "education": EvidenceSource.EDUCATION,
    "skills": EvidenceSource.SKILLS_SECTION,
    "summary": EvidenceSource.SUMMARY,
}

_STRONG_VERBS = ["built", "led", "owned", "designed", "architected", "launched",
                  "scaled", "shipped", "deployed", "migrated", "optimized"]

_MUST_HEADERS = ["must have", "must-have", "must-haves", "required", "requirements",
                  "minimum qualifications"]
_PREFERRED_HEADERS = ["preferred", "nice to have", "nice-to-have", "bonus", "plus"]


def _display(term: str) -> str:
    canon = canonical_name(term)
    return DISPLAY_NAMES.get(canon, canon.title())


def _strength_for_chunk(chunk: dict) -> EvidenceStrength:
    visibility = chunk.get("visibility", "visible")
    if visibility in ("hidden", "off_page", "low_contrast"):
        return EvidenceStrength.SUSPICIOUS

    section = chunk.get("section", "unknown")
    text_low = chunk.get("text", "").lower()

    if section == "experience":
        if re.search(r"\d", chunk["text"]) and any(v in text_low for v in _STRONG_VERBS):
            return EvidenceStrength.DETAILED_ACHIEVEMENT
        return EvidenceStrength.WORK_EXPERIENCE
    if section == "achievements":
        return EvidenceStrength.DETAILED_ACHIEVEMENT
    if section == "projects":
        return EvidenceStrength.PROJECT_EVIDENCE
    if section == "certifications":
        return EvidenceStrength.CERTIFICATION
    if section == "skills":
        return EvidenceStrength.SKILL_LIST_ONLY
    return EvidenceStrength.CONTEXTUAL_MENTION


class MockLLM:
    """Deterministic, zero-dependency stand-in for Gemini. See module
    docstring — this is not a lesser product experience, it's a
    documented, always-available reasoning mode."""

    mode = "mock"

    # ---- JD requirement extraction ------------------------------------------
    def extract_requirements(
        self, jd_text: str, experience_requirement: str
    ) -> RequirementExtractionResult:
        importance = RequirementImportance.MUST_HAVE
        found: dict[str, JobRequirement] = {}

        for raw_line in jd_text.splitlines():
            if not raw_line.strip():
                continue

            # Real JDs write the must/preferred header both as its own line
            # ("Must-have:\nPython, SQL...") AND inline on the same line as
            # the terms ("Must-have: Python, SQL, Docker, AWS."). A pure
            # length check can't tell those apart, so instead find the
            # header phrase's position (if any) and split the line there:
            # text before it keeps the running importance, text from the
            # header onward switches to the new one. That way an inline
            # header never swallows the terms that follow it on the same
            # line.
            low_full = raw_line.lower()
            header_hit = None  # (start_idx, end_idx, new_importance)
            for h in _MUST_HEADERS:
                idx = low_full.find(h)
                if idx != -1 and (header_hit is None or idx < header_hit[0]):
                    header_hit = (idx, idx + len(h), RequirementImportance.MUST_HAVE)
            for h in _PREFERRED_HEADERS:
                idx = low_full.find(h)
                if idx != -1 and (header_hit is None or idx < header_hit[0]):
                    header_hit = (idx, idx + len(h), RequirementImportance.PREFERRED)

            if header_hit is None:
                segments = [(raw_line, importance)]
            else:
                start, end, new_importance = header_hit
                before, after = raw_line[:start], raw_line[end:].lstrip(" :-–—,.")
                segments = []
                if before.strip():
                    segments.append((before, importance))
                if after.strip():
                    segments.append((after, new_importance))
                importance = new_importance  # carries forward to later lines too

            for segment_text, seg_importance in segments:
                low = segment_text.lower()
                for term in TECH_VOCAB:
                    if term in low:
                        canon = canonical_name(term)
                        if canon in found:
                            continue
                        found[canon] = JobRequirement(
                            name=_display(term),
                            category=RequirementCategory.TECHNICAL_SKILL,
                            importance=seg_importance,
                            description=raw_line.strip()[:160],
                            normalized_terms=list(dict.fromkeys([term, canon])),
                            evidence_required=True,
                            weight=1.0,
                        )

        combined = f"{jd_text}\n{experience_requirement}"
        years_match = re.search(r"(\d+)\+?\s*(?:years|yrs)", combined, re.I)
        years_min = float(years_match.group(1)) if years_match else None

        if re.search(r"\b(bachelor|master|degree|b\.?tech|b\.?sc)\b", combined, re.I):
            found.setdefault(
                "degree",
                JobRequirement(
                    name="Relevant Degree",
                    category=RequirementCategory.EDUCATION,
                    importance=RequirementImportance.PREFERRED,
                    description="Degree mentioned in job description.",
                    normalized_terms=["degree", "bachelor", "b.tech"],
                    evidence_required=False,
                    weight=0.5,
                ),
            )

        return RequirementExtractionResult(
            requirements=list(found.values()),
            experience_years_min=years_min,
            experience_years_max=None,
            notes="Extracted by rule-based mock LLM (DEMO_MODE). Only vocabulary "
            "present in the built-in TECH_VOCAB list is recognized — switch to "
            "real mode (Gemini) for open-vocabulary extraction.",
        )

    # ---- resume claim extraction --------------------------------------------
    def extract_claims(self, chunks: list[dict]) -> list[CandidateClaim]:
        claims: dict[str, CandidateClaim] = {}
        for chunk in chunks:
            low = chunk["text"].lower()
            hits = {t for t in TECH_VOCAB if t in low}
            if not hits:
                continue
            strength = _strength_for_chunk(chunk)
            source = _SECTION_TO_SOURCE.get(chunk.get("section", "unknown"))
            if chunk.get("visibility") != "visible":
                source = EvidenceSource.SUSPICIOUS_REGION
            elif source is None:
                source = EvidenceSource.SUMMARY

            for term in hits:
                canon = canonical_name(term)
                ev = EvidenceItem(text=chunk["text"][:220], source=source, page=chunk.get("page"))
                if canon in claims:
                    existing = claims[canon]
                    existing.evidence.append(ev)
                    if _STRENGTH_ORDER.index(strength) > _STRENGTH_ORDER.index(existing.strength):
                        existing.strength = strength
                else:
                    claims[canon] = CandidateClaim(
                        skill_or_topic=_display(term),
                        claim_text=chunk["text"][:220],
                        evidence=[ev],
                        strength=strength,
                        section=chunk.get("section", "unknown"),
                    )
        return list(claims.values())

    # ---- requirement assessment ---------------------------------------------
    def assess_requirement(
        self, requirement: JobRequirement, claims: list[CandidateClaim]
    ) -> RequirementAssessment:
        candidate_terms = {canonical_name(requirement.name)}
        candidate_terms |= {canonical_name(t) for t in requirement.normalized_terms}
        claims_by_canon = {canonical_name(c.skill_or_topic): c for c in claims}

        direct = next((claims_by_canon[t] for t in candidate_terms if t in claims_by_canon), None)

        if direct is not None:
            return self._assess_direct(requirement, direct)

        transfers = transfer_candidates(requirement.name)
        found_transfers = [
            (term, rel, base) for term, rel, base in transfers
            if canonical_name(term) in claims_by_canon
        ]
        if found_transfers:
            return self._assess_transferable(requirement, found_transfers, claims_by_canon)

        return RequirementAssessment(
            requirement=requirement.name,
            status=MatchStatus.NOT_EVIDENCED,
            evidence=[],
            evidence_strength=0.0,
            skill_depth=0.0,
            transferability=None,
            confidence=0.8,
            uncertainty="low",
            verification_needed=False,
            explanation=(
                f"No {requirement.name} evidence was found in work experience, "
                "projects, certifications, or other contextual sections."
            ),
            why_not=(
                f"No clear {requirement.name} evidence was found in work experience, "
                "projects, certifications, or other contextual sections."
            ),
        )

    def _assess_direct(self, requirement: JobRequirement, claim: CandidateClaim) -> RequirementAssessment:
        strength = claim.strength
        ev_float = EVIDENCE_STRENGTH_FLOAT[strength]
        depth = min(1.0, ev_float + 0.05 * (len(claim.evidence) - 1))
        evidence = claim.evidence[:5]

        if strength == EvidenceStrength.SUSPICIOUS:
            return RequirementAssessment(
                requirement=requirement.name,
                status=MatchStatus.POTENTIAL_GAMING,
                evidence=evidence,
                evidence_strength=0.0,
                skill_depth=0.0,
                confidence=0.9,
                uncertainty="low",
                verification_needed=True,
                verification_question=(
                    f"Ask the candidate to directly demonstrate {requirement.name} "
                    "experience — the resume's only mention of it was flagged as "
                    "hidden or low-contrast text."
                ),
                explanation=(
                    f"'{requirement.name}' was found only in a suspicious/hidden "
                    "region of the document and is excluded from standard matching."
                ),
                why_not="Only suspicious-region evidence was found; treated as unevidenced for scoring.",
            )

        if strength in (
            EvidenceStrength.PRODUCTION_OWNERSHIP,
            EvidenceStrength.DETAILED_ACHIEVEMENT,
            EvidenceStrength.WORK_EXPERIENCE,
            EvidenceStrength.PROJECT_EVIDENCE,
        ):
            return RequirementAssessment(
                requirement=requirement.name,
                status=MatchStatus.EXACT_MATCH,
                evidence=evidence,
                evidence_strength=ev_float,
                skill_depth=depth,
                confidence=round(0.75 + 0.2 * ev_float, 2),
                uncertainty="low",
                verification_needed=False,
                explanation=(
                    f"Direct evidence found in {claim.section.replace('_', ' ')}: "
                    f"“{evidence[0].text}”"
                ),
            )

        if strength == EvidenceStrength.CERTIFICATION:
            return RequirementAssessment(
                requirement=requirement.name,
                status=MatchStatus.EQUIVALENT_MATCH,
                evidence=evidence,
                evidence_strength=ev_float,
                skill_depth=depth,
                confidence=0.65,
                uncertainty="medium",
                verification_needed=True,
                verification_question=(
                    f"You're certified in {requirement.name} — can you describe a "
                    "real project where you applied it hands-on?"
                ),
                explanation=f"Certification evidence found: “{evidence[0].text}”",
            )

        if strength == EvidenceStrength.CONTEXTUAL_MENTION:
            return RequirementAssessment(
                requirement=requirement.name,
                status=MatchStatus.PARTIAL_MATCH,
                evidence=evidence,
                evidence_strength=ev_float,
                skill_depth=depth,
                confidence=0.55,
                uncertainty="medium",
                verification_needed=True,
                verification_question=(
                    f"Can you give a specific example of using {requirement.name}?"
                ),
                explanation=f"Only a contextual mention found: “{evidence[0].text}”",
            )

        # SKILL_LIST_ONLY
        return RequirementAssessment(
            requirement=requirement.name,
            status=MatchStatus.PARTIAL_MATCH,
            evidence=evidence,
            evidence_strength=ev_float,
            skill_depth=depth,
            confidence=0.45,
            uncertainty="high",
            verification_needed=True,
            verification_question=(
                f"You list {requirement.name} in your skills — walk me through a "
                "specific time you used it and what you built."
            ),
            explanation=f"'{requirement.name}' appears only in the skills list.",
            why_not=(
                f"'{requirement.name}' appears only in the skills section with no "
                "work, project, or certification evidence."
            ),
        )

    def _assess_transferable(
        self,
        requirement: JobRequirement,
        found_transfers: list[tuple[str, str, float]],
        claims_by_canon: dict[str, CandidateClaim],
    ) -> RequirementAssessment:
        best_term, best_rel, best_base = max(found_transfers, key=lambda t: t[2])
        boost = min(0.15, 0.05 * (len(found_transfers) - 1))
        transferability = round(min(0.95, best_base + boost), 2)

        related_names = ", ".join(_display(t) for t, _, _ in found_transfers)
        related_evidence: list[EvidenceItem] = []
        for term, _, _ in found_transfers:
            c = claims_by_canon[canonical_name(term)]
            related_evidence.extend(c.evidence[:2])

        try:
            relationship = RelationshipType(best_rel)
        except ValueError:
            relationship = RelationshipType.TRANSFERABLE_TO

        return RequirementAssessment(
            requirement=requirement.name,
            status=MatchStatus.TRANSFERABLE,
            evidence=related_evidence[:5],
            evidence_strength=0.0,
            skill_depth=0.0,
            transferability=transferability,
            relationship=relationship,
            confidence=0.65,
            uncertainty="medium",
            verification_needed=True,
            verification_question=(
                f"You have experience with {related_names}. How would you approach "
                f"{requirement.name} given that background?"
            ),
            explanation=(
                f"No direct {requirement.name} evidence found, but the candidate "
                f"demonstrates related experience: {related_names}."
            ),
            why_not=f"{requirement.name}-specific production experience is not directly evidenced.",
        )

    # ---- claim-evidence consistency -----------------------------------------
    def check_claim_consistency(self, claim: CandidateClaim) -> ClaimEvidenceConsistency:
        mapping = {
            EvidenceStrength.PRODUCTION_OWNERSHIP: (ConsistencyStatus.SUPPORTED, "backed by production-ownership evidence"),
            EvidenceStrength.DETAILED_ACHIEVEMENT: (ConsistencyStatus.SUPPORTED, "backed by a detailed achievement"),
            EvidenceStrength.WORK_EXPERIENCE: (ConsistencyStatus.SUPPORTED, "backed by work-experience evidence"),
            EvidenceStrength.PROJECT_EVIDENCE: (ConsistencyStatus.SUPPORTED, "backed by project evidence"),
            EvidenceStrength.CERTIFICATION: (ConsistencyStatus.PARTIALLY_SUPPORTED, "backed only by a certification, no hands-on evidence"),
            EvidenceStrength.CONTEXTUAL_MENTION: (ConsistencyStatus.WEAKLY_SUPPORTED, "backed only by a brief contextual mention"),
            EvidenceStrength.SKILL_LIST_ONLY: (ConsistencyStatus.UNSUPPORTED, "found only in a skills list with no supporting narrative"),
            EvidenceStrength.SUSPICIOUS: (ConsistencyStatus.CONFLICTING, "found only in a suspicious/hidden region of the document"),
        }
        status, reason = mapping[claim.strength]
        return ClaimEvidenceConsistency(
            claim=f"{claim.skill_or_topic} — {claim.claim_text[:80]}",
            status=status,
            explanation=f"This claim is {reason}.",
        )

    # ---- interview questions -------------------------------------------------
    def generate_interview_questions(
        self, assessments: list[RequirementAssessment], max_questions: int = 4
    ) -> list[InterviewQuestion]:
        questions: list[InterviewQuestion] = []

        needing_verification = [a for a in assessments if a.verification_needed and a.verification_question]
        priority = {
            MatchStatus.TRANSFERABLE: 0,
            MatchStatus.PARTIAL_MATCH: 1,
            MatchStatus.EQUIVALENT_MATCH: 2,
        }
        needing_verification.sort(key=lambda a: priority.get(a.status, 3))

        for a in needing_verification[: max(0, max_questions - 1)]:
            questions.append(
                InterviewQuestion(
                    requirement=a.requirement,
                    question=a.verification_question,
                    grounded_in=a.explanation,
                    question_type="verification",
                )
            )

        strong = [a for a in assessments if a.status == MatchStatus.EXACT_MATCH]
        if strong and len(questions) < max_questions:
            top = max(strong, key=lambda a: a.evidence_strength)
            ev_text = top.evidence[0].text if top.evidence else top.requirement
            questions.append(
                InterviewQuestion(
                    requirement=top.requirement,
                    question=(
                        f"Walk me through the {top.requirement} work described as "
                        f"“{ev_text[:100]}” — what was the scale, what was "
                        "the hardest technical problem, and how did you measure success?"
                    ),
                    grounded_in=ev_text,
                    question_type="depth_probe",
                )
            )

        return questions[:max_questions]

    # ---- executive summary ---------------------------------------------------
    def executive_summary(
        self, scores: CandidateScores, assessments: list[RequirementAssessment]
    ) -> str:
        strong = sum(1 for a in assessments if a.status in (MatchStatus.EXACT_MATCH, MatchStatus.EQUIVALENT_MATCH))
        transferable = sum(1 for a in assessments if a.status == MatchStatus.TRANSFERABLE)
        gaps = sum(1 for a in assessments if a.status in (MatchStatus.NOT_EVIDENCED, MatchStatus.POTENTIAL_GAMING, MatchStatus.CONFLICTING))
        low_conf = " Overall evidence confidence is low — treat this analysis as a starting point, not a conclusion." if scores.low_confidence else ""
        return (
            f"Match {scores.match_score:.0f}/100, Evidence Confidence "
            f"{scores.evidence_confidence:.0f}/100, Document Integrity "
            f"{scores.document_integrity:.0f}/100. {strong} requirement(s) are "
            f"directly evidenced, {transferable} rely on transferable (not direct) "
            f"evidence and need verification, and {gaps} show no supporting "
            f"evidence in the resume.{low_conf}"
        )
