"""Real-mode file storage — Supabase Storage, private bucket. Same
untested-but-reviewed caveat as supabase_store.py."""
from __future__ import annotations

import uuid

from app.config import Settings

BUCKET = "resumes"


class SupabaseFileStorage:
    def __init__(self, settings: Settings):
        from supabase import create_client

        key = settings.supabase_service_role_key or settings.supabase_anon_key
        self._client = create_client(settings.supabase_url, key)

    def save(self, org_id: str, file_bytes: bytes, suffix: str = ".pdf") -> str:
        path = f"{org_id}/{uuid.uuid4()}{suffix}"
        self._client.storage.from_(BUCKET).upload(path, file_bytes, {"content-type": "application/pdf"})
        return path

    def read(self, storage_path: str) -> bytes:
        return self._client.storage.from_(BUCKET).download(storage_path)

    def delete(self, storage_path: str) -> None:
        self._client.storage.from_(BUCKET).remove([storage_path])
