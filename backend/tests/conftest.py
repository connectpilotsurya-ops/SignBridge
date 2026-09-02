from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import fitz
import pytest


def _build_pdf(lines: list[tuple[str, float, bool]]) -> bytes:
    """Shared test helper: (text, font size, bold) -> single-page PDF bytes."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    x, y = 56.0, 56.0
    for text, size, bold in lines:
        if text:
            page.insert_text(
                (x, y), text, fontsize=size,
                fontname="hebo" if bold else "helv",
                color=(0.1, 0.1, 0.1),
            )
        y += size + 8
    buf = doc.tobytes()
    doc.close()
    return buf


@pytest.fixture
def build_pdf():
    return _build_pdf


@pytest.fixture()
def client(tmp_path, monkeypatch):
    """A FastAPI TestClient wired to a fresh, isolated SQLite DB + local
    storage dir per test — no shared state between tests, no dependency
    on a running uvicorn process."""
    monkeypatch.setenv("SQLITE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("LOCAL_STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("DEMO_MODE", "true")

    from app.config import get_settings
    from app.llm import client as llm_client_module
    from app.persistence import client as persistence_client_module

    get_settings.cache_clear()
    persistence_client_module.get_store.cache_clear()
    persistence_client_module.get_file_storage.cache_clear()
    llm_client_module.get_llm_client.cache_clear()

    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c

    get_settings.cache_clear()
    persistence_client_module.get_store.cache_clear()
    persistence_client_module.get_file_storage.cache_clear()
    llm_client_module.get_llm_client.cache_clear()


@pytest.fixture()
def auth_headers(client):
    """Signs up a fresh recruiter + org and returns ready-to-use headers."""
    r = client.post(
        "/api/auth/signup",
        json={
            "email": "recruiter@northwind-demo.com",
            "password": "hunter22",
            "display_name": "Test Recruiter",
            "organization_name": "Northwind Test Co",
        },
    )
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}
