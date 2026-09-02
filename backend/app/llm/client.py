"""Single factory every service should call. Never import MockLLM or
GeminiLLM directly elsewhere."""
from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings
from app.llm.base import LLMClient


@lru_cache
def get_llm_client(settings: Settings | None = None) -> LLMClient:
    settings = settings or get_settings()
    if settings.llm_mode == "real":
        from app.llm.gemini_client import GeminiLLM

        return GeminiLLM(settings)
    from app.llm.mock import MockLLM

    return MockLLM()
