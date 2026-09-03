from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Body

from app.api.deps import OrgContext, org_context_dep
from app.persistence.client import get_store
from app.schemas.verification import (
    CandidateClaim,
    VerificationQuestionIn,
    VerificationQuestionOut,
    VerificationRecordIn,
    VerificationRecordOut,
    VerificationSummary,
)
from app.services.analysis_view import load_candidate_analysis
from app.services.verification_engine import analyze_candidate_verifications

router = APIRouter(prefix="/api", tags=["verification"])


@router.post("/applications/{application_id}/verification/analyze", response_model=VerificationSummary)
def analyze_verification(application_id: str, ctx: OrgContext = Depends(org_context_dep)):
    analysis = load_candidate_analysis(ctx.org_id, application_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Application analysis not found")

    store = get_store()
    claims, questions = analyze_candidate_verifications(
        ctx.org_id,
        application_id,
        analysis.requirement_analysis,
        analysis.integrity.model_dump(mode="json"),
    )

    store.save_verification_questions(ctx.org_id, application_id, questions)
    store.append_audit(
        ctx.org_id, "verification.analyzed", "application", application_id, ctx.user.user_id,
        {"claims_count": len(claims), "questions_count": len(questions)},
    )

    saved_q_rows = store.list_verification_questions(ctx.org_id, application_id)
    saved_questions = [VerificationQuestionOut.model_validate(dict(r)) for r in saved_q_rows]
    saved_v_rows = store.list_verification_records(ctx.org_id, application_id)
    saved_verifications = [VerificationRecordOut.model_validate(dict(r)) for r in saved_v_rows]

    return VerificationSummary(
        application_id=application_id,
        claims=claims,
        questions=saved_questions,
        verifications=saved_verifications,
    )


@router.get("/applications/{application_id}/verification/questions", response_model=list[VerificationQuestionOut])
def get_verification_questions(application_id: str, ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    rows = store.list_verification_questions(ctx.org_id, application_id)
    if not rows:
        # Auto-trigger analysis if no questions saved yet
        analysis = load_candidate_analysis(ctx.org_id, application_id)
        if analysis:
            _, questions = analyze_candidate_verifications(
                ctx.org_id, application_id, analysis.requirement_analysis, analysis.integrity.model_dump(mode="json")
            )
            store.save_verification_questions(ctx.org_id, application_id, questions)
            rows = store.list_verification_questions(ctx.org_id, application_id)
    return [VerificationQuestionOut.model_validate(dict(r)) for r in rows]


@router.post("/applications/{application_id}/verification/questions", response_model=VerificationQuestionOut)
def create_custom_question(
    application_id: str, body: VerificationQuestionIn, ctx: OrgContext = Depends(org_context_dep)
):
    store = get_store()
    question_obj = VerificationQuestionOut(
        id=f"custom_{application_id[:6]}_{body.verification_category}",
        organization_id=ctx.org_id,
        application_id=application_id,
        claim_id=body.claim_id,
        requirement_id=body.requirement_id,
        question=body.question,
        purpose=body.purpose,
        evidence_gap=body.evidence_gap,
        verification_category=body.verification_category,
        expected_evidence=body.expected_evidence,
        priority=body.priority,
        status="generated",
        recruiter_notes=None,
        created_at="",
        updated_at="",
    )
    store.save_verification_questions(ctx.org_id, application_id, [question_obj])
    store.append_audit(
        ctx.org_id, "verification.question_created", "application", application_id, ctx.user.user_id,
        {"question": body.question},
    )
    rows = store.list_verification_questions(ctx.org_id, application_id)
    match = [r for r in rows if r["question"] == body.question]
    return VerificationQuestionOut.model_validate(dict(match[0] if match else rows[0]))


@router.patch("/verification/questions/{question_id}", response_model=VerificationQuestionOut)
def update_question(
    question_id: str,
    status: str | None = Body(default=None),
    recruiter_notes: str | None = Body(default=None),
    ctx: OrgContext = Depends(org_context_dep),
):
    store = get_store()
    updated = store.update_verification_question(ctx.org_id, question_id, status=status, recruiter_notes=recruiter_notes)
    if updated is None:
        raise HTTPException(status_code=404, detail="Question not found")
    return VerificationQuestionOut.model_validate(dict(updated))


@router.post("/verification/questions/{question_id}/verify", response_model=VerificationRecordOut)
def submit_question_verification(
    question_id: str, body: VerificationRecordIn, ctx: OrgContext = Depends(org_context_dep)
):
    store = get_store()
    # Find question row to get application_id and claim_id
    with store._conn() as conn:
        q_row = conn.execute("select * from interview_questions where id=? and org_id=?", (question_id, ctx.org_id)).fetchone()
    if q_row is None:
        raise HTTPException(status_code=404, detail="Verification question not found")

    rec = store.save_verification_record(
        ctx.org_id,
        q_row["application_id"],
        q_row["claim_id"],
        question_id,
        ctx.user.user_id,
        body.verification_status.value,
        body.verification_notes,
    )
    store.append_audit(
        ctx.org_id, "verification.recorded", "application", q_row["application_id"], ctx.user.user_id,
        {"question_id": question_id, "status": body.verification_status.value},
    )
    return VerificationRecordOut.model_validate(dict(rec))


@router.get("/applications/{application_id}/verification/summary", response_model=VerificationSummary)
def get_verification_summary(application_id: str, ctx: OrgContext = Depends(org_context_dep)):
    analysis = load_candidate_analysis(ctx.org_id, application_id)
    if analysis is None:
        raise HTTPException(status_code=404, detail="Application analysis not found")

    store = get_store()
    claims, _ = analyze_candidate_verifications(
        ctx.org_id, application_id, analysis.requirement_analysis, analysis.integrity.model_dump(mode="json")
    )

    q_rows = store.list_verification_questions(ctx.org_id, application_id)
    if not q_rows:
        _, generated_q = analyze_candidate_verifications(
            ctx.org_id, application_id, analysis.requirement_analysis, analysis.integrity.model_dump(mode="json")
        )
        store.save_verification_questions(ctx.org_id, application_id, generated_q)
        q_rows = store.list_verification_questions(ctx.org_id, application_id)

    questions = [VerificationQuestionOut.model_validate(dict(r)) for r in q_rows]
    v_rows = store.list_verification_records(ctx.org_id, application_id)
    verifications = [VerificationRecordOut.model_validate(dict(r)) for r in v_rows]

    return VerificationSummary(
        application_id=application_id,
        claims=claims,
        questions=questions,
        verifications=verifications,
    )


@router.get("/public/interview/{application_id}")
def get_candidate_public_interview(application_id: str):
    """Candidate self-access portal endpoint. Returns the top 3 moderate
    interview questions for the candidate to answer in a proctored video call."""
    store = get_store()
    # Try finding application across orgs for public candidate access
    with store._conn() as conn:
        app_row = conn.execute("select * from applications where id=?", (application_id,)).fetchone()
    if app_row is None:
        raise HTTPException(status_code=404, detail="Interview session not found")

    job_row = store.get_job(app_row["org_id"], app_row["job_id"])
    job_title = job_row["title"] if job_row else "Engineering Role"

    q_rows = store.list_verification_questions(app_row["org_id"], application_id)
    if not q_rows:
        analysis = load_candidate_analysis(app_row["org_id"], application_id)
        if analysis:
            _, generated_q = analyze_candidate_verifications(
                app_row["org_id"], application_id, analysis.requirement_analysis, analysis.integrity.model_dump(mode="json")
            )
            store.save_verification_questions(app_row["org_id"], application_id, generated_q)
            q_rows = store.list_verification_questions(app_row["org_id"], application_id)

    # Return top 3 questions for candidate portal
    questions = [dict(r) for r in q_rows[:3]]
    if not questions:
        questions = [
            {
                "id": "q1",
                "question": f"Walk us through the most complex architecture or implementation you delivered for {job_title}.",
                "verification_category": "architecture",
                "purpose": "Verify core system design & technical depth.",
            },
            {
                "id": "q2",
                "question": "Describe a non-trivial production outage or concurrency issue you diagnosed and resolved under pressure.",
                "verification_category": "experience",
                "purpose": "Verify operational troubleshooting and production resilience.",
            },
            {
                "id": "q3",
                "question": "How do you evaluate performance, latency, and memory trade-offs when scaling high-throughput workloads?",
                "verification_category": "scale",
                "purpose": "Verify system scaling limits & performance optimization.",
            },
        ]

    return {
        "application_id": application_id,
        "candidate_label": app_row["display_label"],
        "job_title": job_title,
        "questions": questions,
    }


@router.post("/public/interview/{application_id}/submit")
def submit_candidate_public_interview(application_id: str, answers: list[dict] = Body(...)):
    """Saves candidate's responses for the 3 proctored questions."""
    store = get_store()
    with store._conn() as conn:
        app_row = conn.execute("select * from applications where id=?", (application_id,)).fetchone()
    if app_row is None:
        raise HTTPException(status_code=404, detail="Interview session not found")

    for ans in answers:
        q_id = ans.get("question_id")
        notes = ans.get("answer_text", "")
        if q_id:
            store.update_verification_question(app_row["org_id"], q_id, status="verified", recruiter_notes=f"Candidate Audio/Video Response: {notes}")

    store.append_audit(
        app_row["org_id"], "interview.candidate_completed", "application", application_id, None,
        {"answers_count": len(answers)},
    )
    return {"message": "Candidate proctored interview submitted successfully", "application_id": application_id}
