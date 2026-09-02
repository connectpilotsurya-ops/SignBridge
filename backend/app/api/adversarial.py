"""Spec §29: the adversarial resume simulator, exposed over HTTP.

`POST /api/adversarial/test` runs the six-attack suite (see
app/services/adversarial.py) against either an uploaded PDF or — when
none is supplied — a bundled clean sample resume, so the feature is
demoable with zero setup. Every attack variant is a real PDF pushed
through the real parser and integrity detector; nothing here is
pre-canned.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from app.api.deps import OrgContext, org_context_dep
from app.services.adversarial import AttackReport, run_adversarial_suite
from app.services.sample_resume import build_sample_clean_resume_pdf

router = APIRouter(prefix="/api/adversarial", tags=["adversarial"])


def _report_to_dict(r: AttackReport) -> dict:
    return {
        "attack_type": r.attack_type,
        "label": r.label,
        "injected_keywords": r.injected_keywords,
        "detected": r.detected,
        "matching_impact": r.matching_impact,
        "integrity_impact": r.integrity_impact,
        "flags_triggered": r.flags_triggered,
    }


@router.post("/test")
async def test_adversarial_suite(
    file: UploadFile | None = None,
    ctx: OrgContext = Depends(org_context_dep),
):
    """Runs all six manipulation techniques against a base resume and
    reports, per spec §29's required shape, whether each was detected,
    its effect on matching, and its integrity severity."""
    if file is not None:
        if not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported.")
        base_pdf = await file.read()
        if not base_pdf:
            raise HTTPException(status_code=400, detail="Empty file.")
        source = file.filename
    else:
        base_pdf = build_sample_clean_resume_pdf()
        source = "bundled sample resume (no file uploaded)"

    reports = run_adversarial_suite(base_pdf)
    return {
        "source": source,
        "attacks": [_report_to_dict(r) for r in reports],
        "summary": {
            "total_attacks": len(reports),
            "detected": sum(1 for r in reports if r.detected),
            "excluded_from_matching": sum(1 for r in reports if r.matching_impact == "EXCLUDED"),
        },
    }
