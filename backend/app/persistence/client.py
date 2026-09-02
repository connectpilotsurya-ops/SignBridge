from __future__ import annotations

from functools import lru_cache

from app.config import Settings, get_settings


@lru_cache
def get_store(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.persistence_mode == "real":
        from app.persistence.supabase_store import SupabaseStore

        return SupabaseStore(settings)
    from app.persistence.sqlite_store import SQLiteStore

    return SQLiteStore(settings)


@lru_cache
def get_file_storage(settings: Settings | None = None):
    settings = settings or get_settings()
    if settings.persistence_mode == "real":
        from app.persistence.supabase_storage import SupabaseFileStorage

        return SupabaseFileStorage(settings)
    from app.persistence.local_storage import LocalStorage

    return LocalStorage(settings)
