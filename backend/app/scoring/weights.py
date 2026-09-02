"""
Every tunable number in the scoring engine lives here — spec §23-24 says
the exact percentages should be configurable, so nothing below is
hardcoded inline in engine.py.
"""
from __future__ import annotations

from app.schemas.enums import EvidenceStrength, MatchStatus

# ---- top-level 100-point split (spec §23) ----------------------------------
MUST_HAVE_MAX = 35.0
PREFERRED_MAX = 20.0
EVIDENCE_MAX = 15.0
EXPERIENCE_MAX = 10.0
TRANSFERABILITY_MAX = 10.0
ADAPTABILITY_MAX = 5.0
INTEGRITY_MAX = 5.0

# ---- per-requirement fraction bands by match status (spec §24) ------------
# Each status maps to a (low, high) fraction of that requirement's weight.
# The float used to interpolate within the band differs by status:
#   TRANSFERABLE      -> assessment.transferability
#   everything else   -> assessment.evidence_strength
STATUS_FRACTION_RANGE: dict[MatchStatus, tuple[float, float]] = {
    MatchStatus.EXACT_MATCH: (0.85, 1.00),
    MatchStatus.EQUIVALENT_MATCH: (0.70, 0.85),
    MatchStatus.PARTIAL_MATCH: (0.50, 0.70),
    MatchStatus.TRANSFERABLE: (0.40, 0.70),
    MatchStatus.NOT_EVIDENCED: (0.0, 0.0),
    MatchStatus.CONFLICTING: (0.0, 0.10),
    MatchStatus.POTENTIAL_GAMING: (0.0, 0.0),
    MatchStatus.HUMAN_REVIEW: (0.0, 0.30),
}

# ---- EvidenceStrength enum -> baseline float (spec §14 hierarchy) ---------
# Ordered weakest -> strongest; used when the claim/evidence layer needs to
# seed a numeric evidence_strength before the LLM refines it, and as a floor
# so a skill-list-only claim can never numerically outrank real work
# evidence regardless of what the LLM says.
EVIDENCE_STRENGTH_FLOAT: dict[EvidenceStrength, float] = {
    EvidenceStrength.SUSPICIOUS: 0.0,
    EvidenceStrength.SKILL_LIST_ONLY: 0.20,
    EvidenceStrength.CONTEXTUAL_MENTION: 0.40,
    EvidenceStrength.CERTIFICATION: 0.55,
    EvidenceStrength.PROJECT_EVIDENCE: 0.68,
    EvidenceStrength.WORK_EXPERIENCE: 0.80,
    EvidenceStrength.DETAILED_ACHIEVEMENT: 0.90,
    EvidenceStrength.PRODUCTION_OWNERSHIP: 1.00,
}

ADAPTABILITY_LEVEL_FLOAT = {"low": 0.30, "moderate": 0.65, "high": 1.00}

# A requirement is considered a "gap" (candidate didn't solidly cover it on
# direct evidence) below this fraction — used to decide whether the
# transferability component has anything to reward/penalize.
GAP_FRACTION_THRESHOLD = 0.85

LOW_CONFIDENCE_THRESHOLD = 50.0  # evidence_confidence below this -> low_confidence=True

# ---- CandidateStatus thresholds (spec §32) ---------------------------------
# Human review always wins regardless of match_score — see scoring/gating.py.
STRONG_MATCH_THRESHOLD = 80.0
POTENTIAL_MATCH_THRESHOLD = 60.0
