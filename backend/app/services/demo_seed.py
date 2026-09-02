"""
Spec §46 demo data — seeds one recruiter account, org, job, and a
deliberately varied set of candidates so the product is fully demoable
the moment it's opened, with zero manual setup. Every candidate here is a
real generated PDF pushed through the real parser/detector/scoring
pipeline — nothing is a canned analysis result.

The four candidates are chosen to span the whole story the judging
criteria care about:
  - Priya Natarajan  — genuinely strong, narrative-backed evidence
                        (STRONG_MATCH)
  - Marcus Webb      — a real but partial fit, one honest gap
                        (POTENTIAL_MATCH / LOW_MATCH)
  - Dana Whitfield   — lists the right skills but never demonstrates
                        them narratively — "claims aren't proof"
                        (LOW_MATCH, not flagged as dishonest — just
                        weakly evidenced)
  - Alex Chen        — an otherwise-real resume with hidden white text
                        stuffed in to game the match — the flagship
                        anti-gaming story (REVIEW_REQUIRED)

Safe to re-run: it no-ops if the demo account already exists.
"""
from __future__ import annotations

import fitz

from app.llm.client import get_llm_client
from app.persistence.client import get_store
from app.services.auth import create_demo_token, hash_password
from app.services.sample_resume import build_sample_clean_resume_pdf
from app.services.upload_service import process_resume_upload

DEMO_EMAIL = "demo@synthetixhr.example"
DEMO_PASSWORD = "SynthetixDemo!1"
DEMO_ORG_NAME = "Northwind Analytics (Demo)"

JD_BACKEND_ENGINEER = (
    "We are hiring a Backend Software Engineer to join our platform team.\n"
    "Must-have: Python, SQL, Docker, AWS.\n"
    "Preferred: Kubernetes, Terraform, React.\n"
    "You will design APIs, own services in production, and work closely "
    "with product on data-driven features."
)
JD_BACKEND_EXPERIENCE = "3+ years of professional backend experience"


def _build_pdf(lines: list[tuple[str, float, bool]]) -> bytes:
    """Same layout convention as sample_resume.py: (text, font size, bold)."""
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


def _priya_natarajan_pdf() -> bytes:
    return _build_pdf([
        ("Priya Natarajan", 16, True),
        ("Senior Backend Engineer  |  priya.natarajan@example.com  |  +1 (555) 481-2093", 9.5, False),
        ("", 6, False),
        ("Summary", 12, True),
        ("Backend engineer with 5+ years designing and operating Python services at scale.", 9.5, False),
        ("", 6, False),
        ("Experience", 12, True),
        ("2021 - Present: Senior Software Engineer, Fairbank Systems", 10, True),
        ("Built and scaled a Python/FastAPI billing service handling 40k requests/min in AWS.", 9.5, False),
        ("Designed the PostgreSQL schema and query layer (SQL) for the reporting subsystem.", 9.5, False),
        ("Containerized all services with Docker and led the migration to Kubernetes.", 9.5, False),
        ("Owned the on-call rotation and cut incident response time by half.", 9.5, False),
        ("2019 - 2021: Software Engineer, Larkspur Data", 10, True),
        ("Wrote Python ETL pipelines against SQL data warehouses for the analytics team.", 9.5, False),
        ("Deployed services to AWS using Docker images and infrastructure-as-code.", 9.5, False),
        ("", 6, False),
        ("Skills", 12, True),
        ("Python, SQL, Docker, AWS, Kubernetes, PostgreSQL, FastAPI, Git", 9.5, False),
        ("", 6, False),
        ("Education", 12, True),
        ("B.S. Computer Science, Fairview Institute of Technology, 2019", 9.5, False),
    ])


def _marcus_webb_pdf() -> bytes:
    return _build_pdf([
        ("Marcus Webb", 16, True),
        ("Software Engineer  |  marcus.webb@example.com  |  +1 (555) 771-4420", 9.5, False),
        ("", 6, False),
        ("Summary", 12, True),
        ("Software engineer with 4 years of experience building data-backed web applications.", 9.5, False),
        ("", 6, False),
        ("Experience", 12, True),
        ("2022 - Present: Software Engineer, Cobalt Retail Group", 10, True),
        ("Built Python services for order processing, with SQL-backed inventory queries.", 9.5, False),
        ("Wrote automated tests and documentation for the checkout API.", 9.5, False),
        ("2020 - 2022: Junior Developer, Meridian Software", 10, True),
        ("Maintained a Python/Django application and its SQL database layer.", 9.5, False),
        ("Fixed bugs and shipped small features under senior engineer guidance.", 9.5, False),
        ("", 6, False),
        ("Skills", 12, True),
        ("Python, SQL, Django, Docker, Git, Linux", 9.5, False),
        ("", 6, False),
        ("Education", 12, True),
        ("B.S. Information Systems, Cedarville College, 2020", 9.5, False),
    ])


def _alex_chen_visible_pdf() -> tuple[fitz.Document, float]:
    """Returns the open (not yet saved) document plus the page height, so
    the caller can inject hidden text before saving — this candidate's
    genuine content is real and reasonably good; the gaming is added on
    top of it, exactly like a real dishonest edit would be."""
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    x, y = 56.0, 56.0
    for text, size, bold in [
        ("Alex Chen", 16, True),
        ("Software Engineer  |  alex.chen@example.com  |  +1 (555) 209-6631", 9.5, False),
        ("", 6, False),
        ("Summary", 12, True),
        ("Software engineer with 2 years of experience in backend development.", 9.5, False),
        ("", 6, False),
        ("Experience", 12, True),
        ("2023 - Present: Software Engineer, Hollow Creek Digital", 10, True),
        ("Built internal tools in Python for the operations team.", 9.5, False),
        ("Containerized the team's tools with Docker for local development.", 9.5, False),
        ("2022 - 2023: Intern, Hollow Creek Digital", 10, True),
        ("Assisted with front-end bug fixes and QA testing.", 9.5, False),
        ("", 6, False),
        ("Skills", 12, True),
        ("Python, Docker, Git, HTML, CSS", 9.5, False),
        ("", 6, False),
        ("Education", 12, True),
        ("B.S. Computer Science, Dunmore State University, 2022", 9.5, False),
    ]:
        if text:
            page.insert_text((x, y), text, fontsize=size, fontname="hebo" if bold else "helv", color=(0.1, 0.1, 0.1))
        y += size + 8
    return doc, page.rect.height


def _alex_chen_gamed_pdf() -> bytes:
    """A real resume (see above) with AWS/SQL/Kubernetes/Terraform/React
    stuffed in as white-on-white text — none of those are backed by a
    single real bullet point. This is the flagship "hidden text" story:
    the terms should be excluded from matching, not just down-weighted."""
    doc, page_height = _alex_chen_visible_pdf()
    page = doc[-1]
    page.insert_text(
        (72, page_height - 40),
        "AWS SQL Kubernetes Terraform React",
        fontsize=9, color=(1, 1, 1),
    )
    buf = doc.tobytes()
    doc.close()
    return buf


def demo_data_already_seeded() -> bool:
    store = get_store()
    return store.get_profile_by_email(DEMO_EMAIL) is not None


def run_seed() -> dict:
    """Idempotent: returns existing demo credentials if already seeded,
    otherwise creates the account, job, and four candidates and returns
    the same shape."""
    store = get_store()

    existing = store.get_profile_by_email(DEMO_EMAIL)
    if existing is not None:
        orgs = store.list_orgs_for_user(existing["id"])
        return {
            "already_seeded": True,
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
            "organization": orgs[0]["name"] if orgs else DEMO_ORG_NAME,
        }

    password_hash, salt = hash_password(DEMO_PASSWORD)
    user_id = store.create_user_with_password(DEMO_EMAIL, password_hash, salt, "Demo Recruiter")
    org_id = store.create_organization(DEMO_ORG_NAME)
    store.add_org_member(org_id, user_id, role="owner")
    store.append_audit(org_id, "user.signup", "organization", org_id, user_id, {"email": DEMO_EMAIL, "seed": True})

    job_id = store.create_job(
        org_id, "Backend Software Engineer", "Engineering", "Remote",
        "full_time", JD_BACKEND_ENGINEER, JD_BACKEND_EXPERIENCE,
    )

    llm = get_llm_client()
    result = llm.extract_requirements(JD_BACKEND_ENGINEER, JD_BACKEND_EXPERIENCE)
    import json as _json
    reqs_json = _json.dumps([r.model_dump(mode="json") for r in result.requirements])
    store.set_job_requirements(job_id, reqs_json, result.experience_years_min)
    store.append_audit(
        org_id, "job.requirements_extracted", "job", job_id, user_id,
        {"count": len(result.requirements), "mode": llm.mode, "seed": True},
    )
    job_row = store.get_job(org_id, job_id)

    candidates = [
        ("priya_natarajan_resume.pdf", "Priya Natarajan", _priya_natarajan_pdf()),
        ("marcus_webb_resume.pdf", "Marcus Webb", _marcus_webb_pdf()),
        ("dana_whitfield_resume.pdf", "Dana Whitfield", build_sample_clean_resume_pdf()),
        ("alex_chen_resume.pdf", "Alex Chen", _alex_chen_gamed_pdf()),
    ]

    application_ids = []
    for file_name, candidate_name, pdf_bytes in candidates:
        app_id = process_resume_upload(
            org_id=org_id, user_id=user_id, job_row=job_row,
            file_bytes=pdf_bytes, file_name=file_name,
            candidate_name=candidate_name, candidate_email="",
            llm=llm,
        )
        application_ids.append(app_id)

    # Show the recruiter-override + audit-trail story on the gamed candidate.
    alex_application_id = application_ids[-1]
    alex_application = store.get_application(org_id, alex_application_id)
    store.save_decision(
        org_id, alex_application_id, alex_application["status"], "override", "low_match",
        "Confirmed hidden-text keyword stuffing after manual review — rejecting despite the underlying resume being real.",
        user_id,
    )
    store.append_audit(
        org_id, "recruiter.decision", "application", alex_application_id, user_id,
        {"decision": "override", "final_status": "low_match", "seed": True},
    )

    return {
        "already_seeded": False,
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "organization": DEMO_ORG_NAME,
        "job_id": job_id,
        "application_ids": application_ids,
        "token": create_demo_token(user_id, DEMO_EMAIL),
    }
