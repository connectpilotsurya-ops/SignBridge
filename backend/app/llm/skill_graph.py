"""
A small, hand-curated skill-relationship graph.

This exists for two reasons: (1) it's what DEMO_MODE's rule-based mock LLM
uses to reason about synonyms and transferable skills so the demo is
reliable and explainable without a live model call, and (2) even in real
mode it's passed into the Gemini prompt as grounding context so the model
isn't inventing relationships from scratch every time — spec §16 warns
transferability is a "major differentiator" and should not silently
collapse into "Kubernetes = Yes".

Extend this dict as you add more sample jobs/resumes. It is intentionally
small and readable rather than exhaustive.
"""
from __future__ import annotations

# name -> list of terms that mean the SAME thing (case-insensitive)
SKILL_SYNONYMS: dict[str, list[str]] = {
    "javascript": ["js", "ecmascript"],
    "typescript": ["ts"],
    "kubernetes": ["k8s"],
    "postgresql": ["postgres"],
    "aws": ["amazon web services"],
    "gcp": ["google cloud platform"],
    "azure": ["microsoft azure"],
    "ci/cd": ["continuous integration/continuous deployment", "cicd"],
    "infrastructure as code": ["iac"],
    "machine learning": ["ml"],
    "artificial intelligence": ["ai"],
    "rest": ["rest api", "restful", "representational state transfer"],
}

# requirement -> [(related_skill, relationship_type, base_transferability), ...]
# base_transferability is a 0-1 seed strength; the mock LLM nudges it up/down
# a little based on how many related skills the candidate actually has.
SKILL_TRANSFERS: dict[str, list[tuple[str, str, float]]] = {
    "kubernetes": [
        ("docker", "adjacent_to", 0.55),
        ("aws ecs", "adjacent_to", 0.60),
        ("container orchestration", "related_to", 0.75),
        ("docker swarm", "related_to", 0.70),
        ("helm", "supports", 0.65),
    ],
    "terraform": [
        ("cloudformation", "adjacent_to", 0.60),
        ("ansible", "adjacent_to", 0.50),
        ("infrastructure as code", "equivalent_to", 0.80),
        ("pulumi", "adjacent_to", 0.55),
    ],
    "react": [
        ("vue", "adjacent_to", 0.45),
        ("angular", "adjacent_to", 0.40),
        ("frontend development", "related_to", 0.60),
    ],
    "microservices": [
        ("service-oriented architecture", "equivalent_to", 0.75),
        ("distributed systems", "related_to", 0.65),
        ("docker", "supports", 0.50),
    ],
    "graphql": [
        ("rest api", "adjacent_to", 0.50),
        ("api design", "related_to", 0.60),
    ],
}


def normalize(term: str) -> str:
    return term.strip().lower()


def canonical_name(term: str) -> str:
    """Resolve a synonym back to its canonical requirement name, if any."""
    t = normalize(term)
    for canon, synonyms in SKILL_SYNONYMS.items():
        if t == canon or t in synonyms:
            return canon
    return t


def is_synonym(requirement_name: str, candidate_term: str) -> bool:
    return canonical_name(requirement_name) == canonical_name(candidate_term)


def transfer_candidates(requirement_name: str) -> list[tuple[str, str, float]]:
    return SKILL_TRANSFERS.get(canonical_name(requirement_name), [])
