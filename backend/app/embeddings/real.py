"""Real BAAI/bge-m3 + Qdrant adapters. Only imported when settings.vector_mode
== "real" (i.e. QDRANT_URL is set and DEMO_MODE=false) — see
app/embeddings/client.py. Requires requirements-real.txt."""
from __future__ import annotations

from app.config import Settings
from app.embeddings.base import VectorPoint


class BGEEmbedder:
    mode = "real"

    def __init__(self, settings: Settings):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(settings.embedding_model)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self._model.encode(texts, normalize_embeddings=True).tolist()


class QdrantStore:
    mode = "real"

    def __init__(self, settings: Settings):
        from qdrant_client import QdrantClient
        from qdrant_client.http import models as qmodels

        self._qmodels = qmodels
        self._client = QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)
        self._settings = settings

    def _ensure_collection(self, collection: str, dim: int) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if collection not in existing:
            self._client.create_collection(
                collection_name=collection,
                vectors_config=self._qmodels.VectorParams(size=dim, distance=self._qmodels.Distance.COSINE),
            )

    def upsert(self, collection: str, points: list[VectorPoint]) -> None:
        if not points:
            return
        self._ensure_collection(collection, len(points[0].vector))
        self._client.upsert(
            collection_name=collection,
            points=[
                self._qmodels.PointStruct(id=p.id, vector=p.vector, payload=p.payload)
                for p in points
            ],
        )

    def search(self, collection: str, query_vector: list[float], top_k: int = 8):
        hits = self._client.search(collection_name=collection, query_vector=query_vector, limit=top_k)
        return [(str(h.id), float(h.score), h.payload or {}) for h in hits]

    def clear(self, collection: str) -> None:
        self._client.delete_collection(collection_name=collection)
