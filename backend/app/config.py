"""
Central settings. Everything that decides "demo adapter vs real adapter"
is read from here — services should never check os.environ directly.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    demo_mode: bool = True

    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    qdrant_url: str = ""
    qdrant_api_key: str = ""
    qdrant_collection: str = "synthetix_evidence"

    embedding_model: str = "BAAI/bge-m3"

    api_cors_origins: str = "http://localhost:3000,http://localhost:3001"
    max_upload_mb: int = 10
    sqlite_path: str = "./synthetix_demo.db"
    local_storage_dir: str = "./storage"

    @property
    def cors_origins(self) -> list[str]:
        origins = [o.strip() for o in self.api_cors_origins.split(",") if o.strip()]
        if "*" in origins or self.demo_mode or os.environ.get("VERCEL") or os.environ.get("NETLIFY"):
            return ["*"]
        return origins

    @property
    def effective_sqlite_path(self) -> str:
        if os.environ.get("VERCEL") or os.environ.get("NETLIFY") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return "/tmp/synthetix_demo.db"
        try:
            p = Path(self.sqlite_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            return self.sqlite_path
        except Exception:
            return "/tmp/synthetix_demo.db"

    @property
    def effective_storage_dir(self) -> str:
        if os.environ.get("VERCEL") or os.environ.get("NETLIFY") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
            return "/tmp/storage"
        try:
            p = Path(self.local_storage_dir)
            p.mkdir(parents=True, exist_ok=True)
            return self.local_storage_dir
        except Exception:
            return "/tmp/storage"

    @property
    def llm_mode(self) -> str:
        """'real' only if not demo AND a key is actually present."""
        return "real" if (not self.demo_mode and self.gemini_api_key) else "mock"

    @property
    def vector_mode(self) -> str:
        return "real" if (not self.demo_mode and self.qdrant_url) else "memory"

    @property
    def persistence_mode(self) -> str:
        return "real" if (not self.demo_mode and self.supabase_url) else "sqlite"


@lru_cache
def get_settings() -> Settings:
    return Settings()
