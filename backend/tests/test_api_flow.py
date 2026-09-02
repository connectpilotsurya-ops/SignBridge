"""End-to-end HTTP-level tests against the real FastAPI app (in-process
TestClient, isolated per-test SQLite DB) — spec §37's API surface
exercised the way the frontend actually calls it."""
from __future__ import annotations

JD = (
    "We are hiring a Backend Software Engineer to join our platform team.\n"
    "Must-have: Python, SQL, Docker, AWS.\n"
    "Preferred: Kubernetes, Terraform, React.\n"
    "You will design APIs and own services in production."
)


def _create_analyzed_job(client, headers):
    job = client.post(
        "/api/jobs", headers=headers,
        json={"title": "Backend Software Engineer", "description": JD, "experience_requirement": "3+ years"},
    ).json()
    analyzed = client.post(f"/api/jobs/{job['id']}/analyze", headers=headers).json()
    assert analyzed["requirements_analyzed"] is True
    assert len(analyzed["requirements"]) == 7
    return analyzed


def test_signup_creates_org_and_rejects_duplicate_and_bad_login(client):
    r = client.post(
        "/api/auth/signup",
        json={"email": "a@northwind-demo.com", "password": "correct-horse", "organization_name": "Northwind"},
    )
    assert r.status_code == 200
    dup = client.post(
        "/api/auth/signup",
        json={"email": "a@northwind-demo.com", "password": "anything", "organization_name": "Other Org"},
    )
    assert dup.status_code == 409

    bad_login = client.post("/api/auth/login", json={"email": "a@northwind-demo.com", "password": "wrong"})
    assert bad_login.status_code == 401
    good_login = client.post("/api/auth/login", json={"email": "a@northwind-demo.com", "password": "correct-horse"})
    assert good_login.status_code == 200


def test_job_requirement_extraction_classifies_must_have_vs_preferred(client, auth_headers):
    analyzed = _create_analyzed_job(client, auth_headers)
    by_name = {r["name"]: r["importance"] for r in analyzed["requirements"]}
    assert by_name["Python"] == "must_have"
    assert by_name["Kubernetes"] == "preferred"
    assert analyzed["experience_years_min"] == 3.0


def test_upload_requires_job_requirements_analyzed_first(client, auth_headers, build_pdf):
    job = client.post(
        "/api/jobs", headers=auth_headers,
        json={"title": "Backend Software Engineer", "description": JD, "experience_requirement": "3+ years"},
    ).json()
    pdf = build_pdf([("Someone", 14, True)])
    r = client.post(
        "/api/resumes/upload", headers=auth_headers, data={"job_id": job["id"]},
        files=[("files", ("resume.pdf", pdf, "application/pdf"))],
    )
    assert r.status_code == 400


def test_full_pipeline_and_candidate_status(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    strong_pdf = build_pdf([
        ("Priya Natarajan", 16, True),
        ("Experience", 12, True),
        ("2021 - Present: Senior Software Engineer, Fairbank Systems", 10, True),
        ("Built a Python/FastAPI billing service running in AWS with a PostgreSQL/SQL backend.", 9.5, False),
        ("Containerized all services with Docker and led the migration to Kubernetes.", 9.5, False),
        ("Skills", 12, True),
        ("Python, SQL, Docker, AWS, Kubernetes", 9.5, False),
    ])
    upload = client.post(
        "/api/resumes/upload", headers=auth_headers, data={"job_id": job["id"]},
        files=[("files", ("priya.pdf", strong_pdf, "application/pdf"))],
    ).json()
    assert "error" not in upload["results"][0]
    app_id = upload["results"][0]["application_id"]

    full = client.get(f"/api/applications/{app_id}", headers=auth_headers).json()
    assert full["scores"]["match_score"] > 60
    assert full["analysis_mode"] == "mock"

    for suffix in ["requirements", "evidence", "graph", "score", "questions"]:
        assert client.get(f"/api/applications/{app_id}/{suffix}", headers=auth_headers).status_code == 200
    assert client.get(f"/api/analysis/{app_id}", headers=auth_headers).status_code == 200

    candidates = client.get(f"/api/jobs/{job['id']}/candidates", headers=auth_headers).json()
    assert len(candidates) == 1
    assert candidates[0]["match_score"] == full["scores"]["match_score"]


def test_recruiter_override_preserves_original_status_in_audit_trail(client, auth_headers, build_pdf):
    """Spec §35: the system's own classification is never overwritten —
    only recorded alongside the recruiter's final call."""
    job = _create_analyzed_job(client, auth_headers)
    weak_pdf = build_pdf([("Someone Weak", 16, True), ("Skills", 12, True), ("Python", 9.5, False)])
    upload = client.post(
        "/api/resumes/upload", headers=auth_headers, data={"job_id": job["id"]},
        files=[("files", ("weak.pdf", weak_pdf, "application/pdf"))],
    ).json()
    app_id = upload["results"][0]["application_id"]
    original_status = client.get(f"/api/applications/{app_id}", headers=auth_headers).json()["status"]

    decision = client.post(
        f"/api/applications/{app_id}/decision", headers=auth_headers,
        json={"decision": "override", "final_status": "strong_match", "reason": "Verified in a live technical interview."},
    )
    assert decision.status_code == 200
    body = decision.json()
    assert body["original_status"] == original_status
    assert body["final_status"] == "strong_match"

    after = client.get(f"/api/applications/{app_id}", headers=auth_headers).json()
    assert after["status"] == "strong_match"


def test_override_requires_reason_and_final_status(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    pdf = build_pdf([("Someone", 16, True)])
    upload = client.post(
        "/api/resumes/upload", headers=auth_headers, data={"job_id": job["id"]},
        files=[("files", ("resume.pdf", pdf, "application/pdf"))],
    ).json()
    app_id = upload["results"][0]["application_id"]

    r = client.post(f"/api/applications/{app_id}/decision", headers=auth_headers, json={"decision": "override"})
    assert r.status_code == 400


def test_blind_mode_hides_candidate_name(client, auth_headers, build_pdf):
    job = _create_analyzed_job(client, auth_headers)
    pdf = build_pdf([("Real Name Here", 16, True)])
    upload = client.post(
        "/api/resumes/upload", headers=auth_headers, data={"job_id": job["id"]},
        files=[("files", ("real_name_here.pdf", pdf, "application/pdf"))],
    ).json()
    app_id = upload["results"][0]["application_id"]

    normal = client.get(f"/api/applications/{app_id}", headers=auth_headers).json()
    blind = client.get(f"/api/applications/{app_id}", headers=auth_headers, params={"blind": "true"}).json()
    assert "Real Name" in normal["display_label"] or normal["display_label"] != blind["display_label"]
    assert blind["display_label"].startswith("Candidate #")
    assert blind["blind_mode"] is True
