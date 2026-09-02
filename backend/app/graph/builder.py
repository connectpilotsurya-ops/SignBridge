"""Evidence / capability graph builder — spec §21/§50. Pure data
transformation over already-computed assessments and claims; no new
reasoning happens here, it's purely a re-projection into a node/edge shape
the frontend can render."""
from __future__ import annotations

from app.llm.skill_graph import canonical_name, transfer_candidates
from app.schemas.assessment import RequirementAssessment
from app.schemas.enums import MatchStatus
from app.schemas.evidence import CandidateClaim
from app.schemas.graph import CapabilityGraph, GraphEdge, GraphNode
from app.schemas.requirement import JobRequirement

_STATUS_MAP = {
    MatchStatus.EXACT_MATCH: "direct_evidence",
    MatchStatus.EQUIVALENT_MATCH: "equivalent",
    MatchStatus.PARTIAL_MATCH: "requires_verification",
    MatchStatus.TRANSFERABLE: "transferable",
    MatchStatus.NOT_EVIDENCED: "missing",
    MatchStatus.CONFLICTING: "missing",
    MatchStatus.POTENTIAL_GAMING: "missing",
    MatchStatus.HUMAN_REVIEW: "requires_verification",
}


def build_capability_graph(
    candidate_label: str,
    job_title: str,
    requirements: list[JobRequirement],
    assessments: dict[str, RequirementAssessment],
    claims: list[CandidateClaim],
) -> CapabilityGraph:
    nodes: dict[str, GraphNode] = {
        "candidate": GraphNode(id="candidate", label=candidate_label, kind="candidate"),
        "job": GraphNode(id="job", label=job_title, kind="job"),
    }
    edges: list[GraphEdge] = []
    claims_by_canon = {canonical_name(c.skill_or_topic): c for c in claims}

    def add_skill_node(claim: CandidateClaim, status: str = "direct_evidence") -> str:
        skill_id = f"skill:{claim.skill_or_topic}"
        if skill_id not in nodes:
            nodes[skill_id] = GraphNode(id=skill_id, label=claim.skill_or_topic, kind="skill", status=status)
            edges.append(GraphEdge(source="candidate", target=skill_id, relationship="used"))
        return skill_id

    for req in requirements:
        req_id = f"req:{req.name}"
        a = assessments.get(req.name)
        status = _STATUS_MAP.get(a.status, "missing") if a else "missing"
        nodes[req_id] = GraphNode(id=req_id, label=req.name, kind="requirement", status=status)
        edges.append(GraphEdge(source="job", target=req_id, relationship="requires"))

        if a is None:
            continue

        if a.status in (MatchStatus.EXACT_MATCH, MatchStatus.EQUIVALENT_MATCH, MatchStatus.PARTIAL_MATCH):
            claim = claims_by_canon.get(canonical_name(req.name))
            if claim:
                skill_id = add_skill_node(claim, status)
                edges.append(GraphEdge(source=skill_id, target=req_id, relationship="evidenced_by"))

        elif a.status == MatchStatus.TRANSFERABLE:
            for term, rel, _base in transfer_candidates(req.name):
                claim = claims_by_canon.get(canonical_name(term))
                if claim:
                    skill_id = add_skill_node(claim, "direct_evidence")
                    edges.append(GraphEdge(source=skill_id, target=req_id, relationship=rel))

    return CapabilityGraph(nodes=list(nodes.values()), edges=edges)
