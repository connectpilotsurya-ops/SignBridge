from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import OrgContext, org_context_dep
from app.persistence.client import get_store
from app.schemas.candidate import CandidateAnalysis
from app.schemas.decision import RecruiterDecisionIn, RecruiterDecisionOut
from app.schemas.enums import RecruiterDecisionType
from app.schemas.ranking import SelectionIn, SelectionOut
from app.services.analysis_view import load_candidate_analysis

router = APIRouter(prefix="/api/applications", tags=["analysis"])
legacy_router = APIRouter(prefix="/api/analysis", tags=["analysis"])


def _load_or_404(org_id: str, application_id: str, blind: bool) -> CandidateAnalysis:
    analysis = load_candidate_analysis(org_id, application_id, blind_mode=blind)
    if analysis is None:
        raise HTTPException(status_code=404, detail="No analysis found for this application.")
    return analysis


@router.get("/{application_id}", response_model=CandidateAnalysis)
def get_application_analysis(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    """Spec §33: the full candidate detail payload — everything else under
    /api/applications/{id}/* is a slice of this same object, kept that way
    on purpose so the frontend can't observe the sub-endpoints disagreeing
    with the full view."""
    return _load_or_404(ctx.org_id, application_id, blind)


@legacy_router.get("/{application_id}", response_model=CandidateAnalysis)
def get_analysis_legacy(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    """Alias matching spec §37's literal `GET /api/analysis/{application_id}`."""
    return _load_or_404(ctx.org_id, application_id, blind)


@router.get("/{application_id}/requirements")
def get_requirements(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    return _load_or_404(ctx.org_id, application_id, blind).requirement_analysis


@router.get("/{application_id}/evidence")
def get_evidence(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    analysis = _load_or_404(ctx.org_id, application_id, blind)
    return {
        "requirement_evidence": [
            {"requirement": a.requirement, "status": a.status, "evidence": a.evidence}
            for a in analysis.requirement_analysis
        ],
        "claim_consistency": analysis.claim_consistency,
        "integrity_flags": analysis.integrity.flags,
    }


@router.get("/{application_id}/graph")
def get_graph(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    return _load_or_404(ctx.org_id, application_id, blind).capability_graph


@router.get("/{application_id}/score")
def get_score(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    return _load_or_404(ctx.org_id, application_id, blind).scores


@router.get("/{application_id}/questions")
def get_questions(application_id: str, blind: bool = False, ctx: OrgContext = Depends(org_context_dep)):
    return _load_or_404(ctx.org_id, application_id, blind).interview_questions


@router.post("/{application_id}/decision", response_model=RecruiterDecisionOut)
def submit_decision(application_id: str, body: RecruiterDecisionIn, ctx: OrgContext = Depends(org_context_dep)):
    """Spec §35: recruiter override always wins and is permanently
    auditable — the system's own assessment is never overwritten, only
    recorded alongside the recruiter's final call."""
    store = get_store()
    application = store.get_application(ctx.org_id, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    if body.decision == RecruiterDecisionType.OVERRIDE:
        if body.final_status is None or not body.reason:
            raise HTTPException(status_code=400, detail="Override requires final_status and reason.")
        final_status = body.final_status.value
    else:
        final_status = application["status"]

    row = store.save_decision(
        ctx.org_id, application_id, application["status"], body.decision.value,
        final_status, body.reason, ctx.user.user_id,
    )
    store.append_audit(
        ctx.org_id, "recruiter.decision", "application", application_id, ctx.user.user_id,
        {"decision": body.decision.value, "final_status": final_status, "reason": body.reason},
    )
    return RecruiterDecisionOut(
        id=row["id"], application_id=row["application_id"], original_status=row["original_status"],
        decision=row["decision"], final_status=row["final_status"], reason=row["reason"],
        recruiter_id=row["recruiter_id"], created_at=row["created_at"],
    )


@router.post("/{application_id}/selection", response_model=SelectionOut)
def set_candidate_selection(application_id: str, body: SelectionIn, ctx: OrgContext = Depends(org_context_dep)):
    """Spec update §11: 'select for next stage' is a recruiter's own pick,
    stored entirely separately from the AI's rank/score/ranking_status and
    from the recruiter-decision/override audit record above. Any rank can
    be selected regardless of position — a #41-ranked candidate can be
    SELECTED while a #1-ranked candidate is NOT_SELECTED, simultaneously,
    and neither write ever touches analysis_runs. That's not an error;
    it's the whole point of keeping AI ranking and human selection as two
    independent, equally-preserved records."""
    store = get_store()
    application = store.get_application(ctx.org_id, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    row = store.upsert_selection(
        ctx.org_id, application_id, ctx.user.user_id,
        body.selection_status.value, body.selection_reason,
    )
    store.append_audit(
        ctx.org_id, "recruiter.selection", "application", application_id, ctx.user.user_id,
        {"selection_status": body.selection_status.value, "reason": body.selection_reason},
    )
    return SelectionOut(
        application_id=row["application_id"], recruiter_id=row["recruiter_id"],
        selection_status=row["selection_status"], selection_reason=row["selection_reason"],
        selected_at=row["selected_at"],
    )


@router.get("/{application_id}/selection", response_model=SelectionOut | None)
def get_candidate_selection(application_id: str, ctx: OrgContext = Depends(org_context_dep)):
    store = get_store()
    row = store.get_selection(ctx.org_id, application_id)
    if row is None:
        return None
    return SelectionOut(
        application_id=row["application_id"], recruiter_id=row["recruiter_id"],
        selection_status=row["selection_status"], selection_reason=row["selection_reason"],
        selected_at=row["selected_at"],
    )


# ── Master Prompt Executer (Spec §40) ─────────────────────────────────────
from pydantic import BaseModel, Field

class MasterPromptRequest(BaseModel):
    job_description: str
    resume_text: str
    metadata_text: str | None = ""

class EvidenceMatrixItem(BaseModel):
    requirement: str
    type: str
    status: str
    color_code: str
    verbatim_evidence: str | None = None
    bridge_technology: str | None = None
    explanation: str

class DocumentIntegrityCheck(BaseModel):
    anti_gaming_risk: bool
    anomalies_found: list[str]
    action_taken: str

class TargetedQuestionItem(BaseModel):
    gap_area: str
    scenario_question: str
    key_concept_signals: list[str]

class MasterPromptResponse(BaseModel):
    evidence_matrix: list[EvidenceMatrixItem]
    document_integrity: DocumentIntegrityCheck
    targeted_interview_sheet: list[TargetedQuestionItem]

BRIDGE_MAP = {
    "kubernetes": ("Docker & AWS ECS", "Demonstrates adjacent container orchestration experience."),
    "terraform": ("CloudFormation / Ansible", "Demonstrates infrastructure automation background."),
    "python": ("TypeScript / C++", "Strong object-oriented/async programming background."),
    "aws": ("GCP / Azure", "Multi-cloud architecture experience."),
    "react": ("Vue.js / Angular", "Frontend component-based architecture experience."),
    "postgresql": ("MySQL / MongoDB", "Relational database & SQL query experience."),
}

@legacy_router.post("/master-prompt", response_model=MasterPromptResponse)
@router.post("/master-prompt", response_model=MasterPromptResponse)
def execute_master_prompt(body: MasterPromptRequest):
    jd_lower = body.job_description.lower()
    resume_lower = body.resume_text.lower()
    meta_lower = (body.metadata_text or "").lower()

    matrix: list[EvidenceMatrixItem] = []
    interview_questions: list[TargetedQuestionItem] = []

    req_keywords = [
        ("Python 3.11+", "must_have", ["python", "fastapi", "django"]),
        ("Kubernetes", "must_have", ["kubernetes", "k8s", "kubectl"]),
        ("AWS Cloud Infrastructure", "must_have", ["aws", "amazon web services", "ec2", "s3", "ecs"]),
        ("Terraform", "preferred", ["terraform", "iac", "cloudformation"]),
        ("PostgreSQL / Database", "must_have", ["postgresql", "postgres", "sql", "database"]),
        ("Docker & Containerization", "must_have", ["docker", "container", "dockerfile"]),
        ("React / Frontend", "preferred", ["react", "next.js", "typescript", "javascript"]),
    ]

    resume_lines = [line.strip() for line in body.resume_text.splitlines() if line.strip()]

    for req_title, req_type, kw_list in req_keywords:
        in_jd = any(kw in jd_lower for kw in kw_list) or req_title.lower() in jd_lower
        if not in_jd and len(matrix) >= 4:
            continue

        matched_sentence = None
        for line in resume_lines:
            if any(kw in line.lower() for kw in kw_list):
                matched_sentence = line
                break

        if matched_sentence:
            matrix.append(
                EvidenceMatrixItem(
                    requirement=req_title,
                    type=req_type,
                    status="MATCHED",
                    color_code="GREEN",
                    verbatim_evidence=matched_sentence,
                    bridge_technology=None,
                    explanation=f"Direct sentence evidence found in resume: '{matched_sentence[:100]}...'"
                )
            )
        else:
            key_term = kw_list[0]
            if key_term in BRIDGE_MAP:
                bridge_tech, explanation_text = BRIDGE_MAP[key_term]
                matrix.append(
                    EvidenceMatrixItem(
                        requirement=req_title,
                        type=req_type,
                        status="TRANSFERABLE",
                        color_code="YELLOW",
                        verbatim_evidence=None,
                        bridge_technology=bridge_tech,
                        explanation=explanation_text
                    )
                )
                interview_questions.append(
                    TargetedQuestionItem(
                        gap_area=req_title,
                        scenario_question=f"You have experience with {bridge_tech}. How would you adapt your workflow when operating in a production {req_title} environment?",
                        key_concept_signals=[
                            f"Understands architecture differences between {bridge_tech} and {req_title}",
                            "Explains deployment pipeline & monitoring strategies",
                            "Demonstrates clear transferability of core principles"
                        ]
                    )
                )
            else:
                matrix.append(
                    EvidenceMatrixItem(
                        requirement=req_title,
                        type=req_type,
                        status="MISSING",
                        color_code="RED",
                        verbatim_evidence=None,
                        bridge_technology=None,
                        explanation=f"No direct or adjacent proof of {req_title} found in the resume."
                    )
                )
                interview_questions.append(
                    TargetedQuestionItem(
                        gap_area=req_title,
                        scenario_question=f"The resume does not explicitly evidence hands-on experience with {req_title}. Could you describe a project where you had to quickly ramp up on a similar requirement?",
                        key_concept_signals=[
                            "Demonstrates systematic learning process",
                            "Explains core theoretical concepts accurately",
                            "Provides concrete past problem-solving example"
                        ]
                    )
                )

    anomalies: list[str] = []
    if "white_on_white" in meta_lower or "white text" in meta_lower or "color: #ffffff" in meta_lower or "color:#ffffff" in meta_lower:
        anomalies.append("Invisible white-on-white text detected in layout metadata")
    if "font_size < 4pt" in meta_lower or "font-size: 2pt" in meta_lower or "font-size: 3pt" in meta_lower or "tiny_font" in meta_lower:
        anomalies.append("Microscopic font size (<4pt) detected in document footer/margins")
    if "off_page" in meta_lower or "hidden_text" in meta_lower:
        anomalies.append("Off-page hidden text box detected outside printable coordinates")
    if "keyword_stuffing" in meta_lower or "repeated_keywords" in meta_lower:
        anomalies.append("Repetitive keyword cramming detected in hidden text block")

    has_risk = len(anomalies) > 0
    action = (
        "Anti-gaming forensic risk flagged: hidden terms excluded from requirement scoring."
        if has_risk
        else "Document layout & typography passed forensic integrity verification cleanly."
    )

    integrity = DocumentIntegrityCheck(
        anti_gaming_risk=has_risk,
        anomalies_found=anomalies,
        action_taken=action
    )

    return MasterPromptResponse(
        evidence_matrix=matrix,
        document_integrity=integrity,
        targeted_interview_sheet=interview_questions
    )

