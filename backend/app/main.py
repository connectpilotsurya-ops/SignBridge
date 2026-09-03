"""
SYNTHETIX HR — FastAPI application entrypoint.

Assembles every router built for the MVP (spec §37's API surface) and
wires CORS from Settings so the Next.js frontend (dev server on
localhost:3000 by default, configurable via API_CORS_ORIGINS) can call it.

Run with:  uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import adversarial, analysis, auth, jobs, resumes, verification
from app.config import get_settings


def _seed_demo_data() -> None:
    """Spec §46: the app should be instantly demoable with zero manual
    setup. Only runs against the local SQLite store (never a real
    Supabase database) and is a no-op if already seeded."""
    settings = get_settings()
    if settings.persistence_mode == "real":
        return
    from app.services.demo_seed import run_seed

    try:
        run_seed()
    except Exception:  # noqa: BLE001 — seeding must never block the app from starting
        import logging

        logging.getLogger("uvicorn.error").exception("Demo data seeding failed")


@asynccontextmanager
async def _lifespan(app: FastAPI):
    _seed_demo_data()
    yield


app = FastAPI(
    title="SYNTHETIX HR API",
    description="Proof before score. Don't score the claim. Score the evidence.",
    version="0.1.0",
    lifespan=_lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(jobs.router)
app.include_router(resumes.router)
app.include_router(analysis.router)
app.include_router(analysis.legacy_router)
app.include_router(adversarial.router)
app.include_router(verification.router)


@app.get("/")
def root():
    settings = get_settings()
    return {
        "name": "SYNTHETIX HR API",
        "tagline": "Proof before score.",
        "demo_mode": settings.demo_mode,
        "llm_mode": settings.llm_mode,
        "vector_mode": settings.vector_mode,
        "persistence_mode": settings.persistence_mode,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
