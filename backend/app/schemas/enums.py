"""
Every controlled vocabulary used across the pipeline. Centralized so the
LLM prompts, the Pydantic validators, and the frontend badges can never
drift out of sync with each other.
"""
from enum import Enum


class RequirementCategory(str, Enum):
    TECHNICAL_SKILL = "technical_skill"
    DOMAIN_SKILL = "domain_skill"
    EXPERIENCE = "experience"
    EDUCATION = "education"
    CERTIFICATION = "certification"


class RequirementImportance(str, Enum):
    MUST_HAVE = "must_have"
    PREFERRED = "preferred"


class ResumeStatus(str, Enum):
    UPLOADED = "uploaded"
    PARSING = "parsing"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    REVIEW_REQUIRED = "review_required"


class Visibility(str, Enum):
    VISIBLE = "visible"
    LOW_CONTRAST = "low_contrast"
    HIDDEN = "hidden"
    OFF_PAGE = "off_page"


class EvidenceSource(str, Enum):
    WORK_EXPERIENCE = "work_experience"
    PROJECT = "project"
    ACHIEVEMENT = "achievement"
    CERTIFICATION = "certification"
    EDUCATION = "education"
    SKILLS_SECTION = "skills_section"
    SUMMARY = "summary"
    SUSPICIOUS_REGION = "suspicious_region"


class EvidenceStrength(str, Enum):
    """Ordered weakest → strongest. Keep this order — scoring.weights relies on it."""
    SUSPICIOUS = "suspicious"
    SKILL_LIST_ONLY = "skill_list_only"
    CONTEXTUAL_MENTION = "contextual_mention"
    CERTIFICATION = "certification"
    PROJECT_EVIDENCE = "project_evidence"
    WORK_EXPERIENCE = "work_experience"
    DETAILED_ACHIEVEMENT = "detailed_achievement"
    PRODUCTION_OWNERSHIP = "production_ownership"


class MatchStatus(str, Enum):
    EXACT_MATCH = "exact_match"
    EQUIVALENT_MATCH = "equivalent_match"
    PARTIAL_MATCH = "partial_match"
    TRANSFERABLE = "transferable"
    NOT_EVIDENCED = "not_evidenced"
    CONFLICTING = "conflicting"
    POTENTIAL_GAMING = "potential_gaming"
    HUMAN_REVIEW = "human_review"


class ConsistencyStatus(str, Enum):
    SUPPORTED = "supported"
    PARTIALLY_SUPPORTED = "partially_supported"
    WEAKLY_SUPPORTED = "weakly_supported"
    UNSUPPORTED = "unsupported"
    CONFLICTING = "conflicting"


class SkillDepthLevel(str, Enum):
    MENTIONED = "mentioned"
    FAMILIAR = "familiar"
    PRACTICAL = "practical"
    ADVANCED = "advanced"
    PRODUCTION = "production"


class IntegritySeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class IntegrityCategory(str, Enum):
    NORMAL = "normal"
    SUSPICIOUS = "suspicious"
    HIGH_RISK = "high_risk"


class IntegrityFlagType(str, Enum):
    HIDDEN_TEXT = "hidden_text"
    NEAR_WHITE_TEXT = "near_white_text"
    TINY_FONT = "tiny_font"
    SUSPICIOUS_FOOTER = "suspicious_footer"
    OFF_PAGE_TEXT = "off_page_text"
    HIGH_KEYWORD_DENSITY = "high_keyword_density"
    REPEATED_KEYWORDS = "repeated_keywords"
    SKILLS_ONLY_CLUSTER = "skills_only_cluster"


class RelationshipType(str, Enum):
    EQUIVALENT_TO = "equivalent_to"
    RELATED_TO = "related_to"
    ADJACENT_TO = "adjacent_to"
    SUPPORTS = "supports"
    PREREQUISITE_FOR = "prerequisite_for"
    TRANSFERABLE_TO = "transferable_to"


class CandidateStatus(str, Enum):
    STRONG_MATCH = "strong_match"
    POTENTIAL_MATCH = "potential_match"
    REVIEW_REQUIRED = "review_required"
    LOW_MATCH = "low_match"


class RankingStatus(str, Enum):
    """Spec update: 'ranking, not shortlisting'. A descriptive ranking
    tier, never a hiring decision — see app/scoring/ranking.py. Distinct
    from CandidateStatus, which is the recruiter's own decision/override
    classification (a separate, human-owned concept)."""

    TOP_MATCH = "top_match"
    STRONG_MATCH = "strong_match"
    POTENTIAL_MATCH = "potential_match"
    LOWER_MATCH = "lower_match"
    HUMAN_REVIEW_REQUIRED = "human_review_required"


class SelectionStatus(str, Enum):
    """A recruiter's own manual pick for the next hiring stage — stored
    entirely separately from the AI's rank/score, and from the recruiter
    decision/override record. Any rank can be selected regardless of
    position; this is deliberate, preserved human judgment (spec §11)."""

    SELECTED = "selected"
    NOT_SELECTED = "not_selected"
    UNDER_REVIEW = "under_review"


class RecruiterDecisionType(str, Enum):
    AGREE = "agree"
    OVERRIDE = "override"
    NEEDS_FURTHER_REVIEW = "needs_further_review"


class OrgRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    RECRUITER = "recruiter"
    VIEWER = "viewer"


class AnalysisConfidence(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
