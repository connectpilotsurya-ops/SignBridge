from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.api.deps import OrgContext, org_context_dep
from app.config import get_settings
from app.llm.client import get_llm_client
from app.persistence.client import get_file_storage, get_store
from app.services.upload_service import process_resume_upload

router = APIRouter(prefix="/api/resumes", tags=["resumes"])


@router.post("/upload")
async def upload_resumes(
    job_id: str = Form(...),
    files: list[UploadFile] = File(...),
    ctx: OrgContext = Depends(org_context_dep),
):
    """Spec §9: supports multiple resumes in one call. Each file is
    validated (extension, size) before anything is written to disk;
    parsing/analysis failures for one file never abort the batch — spec
    §40 says analysis failure must degrade to ANALYSIS_INCOMPLETE +
    HUMAN_REVIEW_REQUIRED for that candidate, not a 500 for everyone."""
    store = get_store()
    settings = get_settings()
    job_row = store.get_job(ctx.org_id, job_id)
    if job_row is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not bool(job_row["requirements_analyzed"]):
        raise HTTPException(
            status_code=400,
            detail="Analyze the job's requirements first (POST /api/jobs/{job_id}/analyze).",
        )

    llm = get_llm_client()
    results = []
    for f in files:
        if not f.filename.lower().endswith(".pdf"):
            results.append({"file_name": f.filename, "error": "Only PDF files are supported."})
            continue

        body = await f.read()
        if len(body) > settings.max_upload_mb * 1024 * 1024:
            results.append({"file_name": f.filename, "error": f"File exceeds {settings.max_upload_mb}MB limit."})
            continue
        if len(body) == 0:
            results.append({"file_name": f.filename, "error": "Empty file."})
            continue

        try:
            application_id = process_resume_upload(
                org_id=ctx.org_id,
                user_id=ctx.user.user_id,
                job_row=job_row,
                file_bytes=body,
                file_name=f.filename,
                candidate_name=f.filename.rsplit(".", 1)[0],
                candidate_email="",
                llm=llm,
            )
            results.append({"file_name": f.filename, "application_id": application_id})
        except Exception as exc:  # noqa: BLE001 — never let one bad file 500 the whole batch
            results.append({"file_name": f.filename, "error": f"Processing failed: {exc}"})

    return {"results": results}


@router.get("/{resume_id}")
def get_resume_status(resume_id: str, ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    row = store.get_resume(ctx.org_id, resume_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Resume not found")
    return {
        "id": row["id"], "file_name": row["file_name"], "status": row["status"],
        "page_count": row["page_count"], "failure_reason": row["failure_reason"] if "failure_reason" in row.keys() else None,
    }
