"""
Zero-dependency stand-ins for BGE-M3 + Qdrant.

HashingEmbedder is a deterministic character-n-gram hashing vectorizer —
not a learned model, so don't expect it to catch deep semantic paraphrase
the way BGE-M3 would. It's good enough for its actual job in this
pipeline: lexically ranking which resume chunks are worth sending to the
assessment step for a given requirement (spec §42's "retrieve only
relevant evidence"), so demo mode never needs a model download. Swapping
in real BGE-M3 + Qdrant (requirements-real.txt) is a drop-in behind the
same Protocol in base.py — nothing else in the codebase changes.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import defaultdict

from app.embeddings.base import VectorPoint

_DIM = 256
_TOKEN_RE = re.compile(r"[a-z0-9+.#]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN_RE.findall(text.lower())


def _ngrams(token: str, n: int = 3) -> list[str]:
    if len(token) <= n:
        return [token]
    return [token[i : i + n] for i in range(len(token) - n + 1)]


class HashingEmbedder:
    mode = "hash"

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed_one(t) for t in texts]

    def _embed_one(self, text: str) -> list[float]:
        vec = [0.0] * _DIM
        for tok in _tokens(text):
            for gram in _ngrams(tok):
                h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                idx = h % _DIM
                sign = 1.0 if (h // _DIM) % 2 == 0 else -1.0
                vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))  # both pre-normalized


class MemoryVectorStore:
    mode = "memory"

    def __init__(self) -> None:
        self._collections: dict[str, dict[str, VectorPoint]] = defaultdict(dict)

    def upsert(self, collection: str, points: list[VectorPoint]) -> None:
        for p in points:
            self._collections[collection][p.id] = p

    def search(self, collection: str, query_vector: list[float], top_k: int = 8) -> list[tuple[str, float, dict]]:
        points = self._collections.get(collection, {})
        scored = [(p.id, _cosine(query_vector, p.vector), p.payload) for p in points.values()]
        scored.sort(key=lambda t: t[1], reverse=True)
        return scored[:top_k]

    def clear(self, collection: str) -> None:
        self._collections.pop(collection, None)
