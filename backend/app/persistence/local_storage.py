"""File storage for DEMO_MODE — plain local disk under LOCAL_STORAGE_DIR,
standing in for a private Supabase Storage bucket (spec §41: "no resume
files exposed publicly" — this directory is never served by a static
route, only read back through the API after an org-membership check)."""
from __future__ import annotations

import uuid
from pathlib import Path

from app.config import Settings


class LocalStorage:
    def __init__(self, settings: Settings):
        self.root = Path(settings.effective_storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, org_id: str, file_bytes: bytes, suffix: str = ".pdf") -> str:
        rel = f"{org_id}/{uuid.uuid4()}{suffix}"
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        return rel

    def read(self, storage_path: str) -> bytes:
        return (self.root / storage_path).read_bytes()

    def delete(self, storage_path: str) -> None:
        p = self.root / storage_path
        if p.exists():
            p.unlink()
