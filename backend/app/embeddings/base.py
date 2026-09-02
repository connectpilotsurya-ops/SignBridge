"""Interfaces for the semantic-retrieval layer — spec §15/§21/§42. The
scoring/assessment logic never queries these directly for "proof"; per
spec §15, embedding similarity is a *retrieval* signal only, used to
narrow which evidence chunks get sent to the assessment step (mock or
real) — never treated as a match by itself."""
from __future__ import annotations

from typing import Protocol


class EmbeddingClient(Protocol):
    mode: str  # "hash" | "real"

    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...


class VectorPoint:
    __slots__ = ("id", "vector", "payload")

    def __init__(self, id: str, vector: list[float], payload: dict):
        self.id = id
        self.vector = vector
        self.payload = payload


class VectorStore(Protocol):
    mode: str  # "memory" | "real"

    def upsert(self, collection: str, points: list[VectorPoint]) -> None: ...

    def search(self, collection: str, query_vector: list[float], top_k: int = 8) -> list[tuple[str, float, dict]]:
        """Returns (id, similarity_score, payload) tuples, highest score first."""
        ...

    def clear(self, collection: str) -> None: ...
