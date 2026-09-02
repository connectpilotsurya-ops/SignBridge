from __future__ import annotations

from pydantic import BaseModel, Field


class GraphNode(BaseModel):
    """Spec §21/§50. `kind` drives the frontend's node color/shape."""

    id: str
    label: str
    kind: str  # candidate | job | requirement | skill | experience | project | achievement | certification | evidence
    status: str | None = None  # direct_evidence | equivalent | transferable | missing | requires_verification


class GraphEdge(BaseModel):
    source: str
    target: str
    relationship: str  # requires | used | built | worked_at | supports | adjacent_to | equivalent_to | transferable_to | evidenced_by


class CapabilityGraph(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)
