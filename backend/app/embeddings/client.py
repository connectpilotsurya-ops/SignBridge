from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.embeddings.base import EmbeddingClient, VectorStore


@lru_cache
def get_embedding_client(settings: Settings | None = None) -> EmbeddingClient:
    settings = settings or get_settings()
    if settings.vector_mode == "real":
        from app.embeddings.real import BGEEmbedder

        return BGEEmbedder(settings)
    from app.embeddings.memory import HashingEmbedder

    return HashingEmbedder()


@lru_cache
def get_vector_store(settings: Settings | None = None) -> VectorStore:
    settings = settings or get_settings()
    if settings.vector_mode == "real":
        from app.embeddings.real import QdrantStore

        return QdrantStore(settings)
    from app.embeddings.memory import MemoryVectorStore

    return MemoryVectorStore()
